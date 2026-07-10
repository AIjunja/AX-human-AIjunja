"""Build and audit evidence packets for customer-support answer drafts."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

RISK_PATTERNS = {
    "service_wide_outage": re.compile(r"(서비스|시스템|전체).{0,8}(전체\s*)?(장애|먹통)"),
    "root_cause": re.compile(r"(원인은|원인으로|때문에 발생|장애 원인)"),
    "recovery_complete": re.compile(r"(복구\s*완료|완전히\s*복구|정상화\s*완료)"),
    "performance_claim": re.compile(r"(성과|해결률|응답률|전환율).{0,12}(향상|증가|개선|상승)"),
}

CONCEPTS = {
    "source": ("출처",),
    "missing": ("없", "표시되지", "누락"),
    "official": ("공식",),
    "document": ("문서", "가이드", "도움말"),
    "verify": ("확인", "체크", "검수"),
    "answer": ("답변", "응답"),
    "ai": ("ai", "인공지능"),
    "faq": ("faq", "자주 묻는 질문"),
}


class InputError(ValueError):
    pass


def _public_https(url: object) -> bool:
    if not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        _ = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        return False
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    return address.is_global and not any((address.is_multicast, address.is_reserved, address.is_unspecified))


def _require_list(value: object, name: str) -> list:
    if not isinstance(value, list) or not value:
        raise InputError(f"{name} must be a non-empty array")
    return value


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" \t\r\n.,!?。！？”'‘’\"")


def _concepts(text: str) -> set[str]:
    normalized = _normalize(text)
    return {name for name, variants in CONCEPTS.items() if any(v in normalized for v in variants)}


def _semantic_candidate(claim: str, quote: str) -> bool:
    claim_concepts, quote_concepts = _concepts(claim), _concepts(quote)
    if len(claim_concepts) < 2:
        return False
    common = claim_concepts & quote_concepts
    return len(common) >= 2 and len(common) / len(claim_concepts) >= 0.4


def _direct_match(claim: str, quote: str) -> bool:
    claim_norm, quote_norm = _normalize(claim), _normalize(quote)
    return bool(claim_norm) and (claim_norm == quote_norm or claim_norm in quote_norm)


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.findall(r"[^.!?。！？\r\n]+[.!?。！？]?", text) if part.strip()]


def _validated_sources(sources: list) -> tuple[dict[str, dict], dict[str, dict]]:
    source_index: dict[str, dict] = {}
    evidence_index: dict[str, dict] = {}
    for source in sources:
        if not isinstance(source, dict):
            raise InputError("each source must be an object")
        sid, url = source.get("source_id"), source.get("url")
        title, retrieved_at = source.get("title"), source.get("retrieved_at")
        if not all(isinstance(v, str) and v.strip() for v in (sid, title, retrieved_at)):
            raise InputError("source_id, title, and retrieved_at are required strings")
        if sid in source_index:
            raise InputError(f"duplicate source_id: {sid}")
        if not _public_https(url):
            raise InputError(f"source {sid} must use a public HTTPS URL")
        source_text = source.get("source_text")
        content_sha256 = source.get("content_sha256")
        if not isinstance(source_text, str) and not (
            isinstance(content_sha256, str) and re.fullmatch(r"[0-9a-fA-F]{64}", content_sha256)
        ):
            raise InputError(f"source {sid} needs source_text or content_sha256")
        calculated = hashlib.sha256(source_text.encode("utf-8")).hexdigest() if isinstance(source_text, str) else None
        if content_sha256 and calculated and content_sha256.lower() != calculated:
            raise InputError(f"source {sid} content_sha256 does not match source_text")
        source_index[sid] = {
            "title": title, "url": url, "retrieved_at": retrieved_at,
            "source_text": source_text, "content_sha256": content_sha256 or calculated,
        }
        for ev in source.get("evidence", []):
            if not isinstance(ev, dict):
                raise InputError("each evidence must be an object")
            eid, quote, location = ev.get("evidence_id"), ev.get("quote"), ev.get("location")
            if not all(isinstance(v, str) and v.strip() for v in (eid, quote)):
                raise InputError("evidence_id and exact quote are required strings")
            if eid in evidence_index:
                raise InputError(f"duplicate evidence_id: {eid}")
            if not isinstance(location, dict):
                raise InputError(f"evidence {eid} needs location")
            verified = False
            if isinstance(source_text, str):
                start, end = location.get("start"), location.get("end")
                if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end < start:
                    raise InputError(f"evidence {eid} quote location is invalid")
                if source_text[start:end] != quote:
                    raise InputError(f"evidence {eid} quote location does not match source_text")
                verified = True
            evidence_index[eid] = {
                "source_id": sid, "quote": quote, "location": location,
                "quote_verified": verified,
            }
    return source_index, evidence_index


def audit(data: object) -> dict:
    if not isinstance(data, dict):
        raise InputError("root must be an object")
    sources = _require_list(data.get("sources"), "sources")
    answers = _require_list(data.get("answers"), "answers")
    source_index, evidence_index = _validated_sources(sources)

    results, publishable, actions, reviews = [], [], [], []
    seen_claims: set[str] = set()
    for answer in answers:
        if not isinstance(answer, dict) or not isinstance(answer.get("answer_id"), str):
            raise InputError("each answer needs answer_id")
        claims = _require_list(answer.get("claims"), f"answer {answer.get('answer_id')}.claims")
        rendered, answer_ready = [], True
        for claim in claims:
            if not isinstance(claim, dict):
                raise InputError("each claim must be an object")
            cid, text = claim.get("claim_id"), claim.get("text")
            if not all(isinstance(v, str) and v.strip() for v in (cid, text)):
                raise InputError("claim_id and text are required strings")
            if cid in seen_claims:
                raise InputError(f"duplicate claim_id: {cid}")
            seen_claims.add(cid)
            ids = claim.get("evidence_ids")
            if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids):
                raise InputError(f"claim {cid}.evidence_ids must be an array of strings")
            missing = sorted(set(ids) - evidence_index.keys())
            valid_ids = [eid for eid in ids if eid in evidence_index]
            verified = [evidence_index[eid] for eid in valid_ids if evidence_index[eid]["quote_verified"]]
            direct_ids = [eid for eid in valid_ids if evidence_index[eid]["quote_verified"] and _direct_match(text, evidence_index[eid]["quote"])]
            semantic_ids = [eid for eid in valid_ids if evidence_index[eid]["quote_verified"] and _semantic_candidate(text, evidence_index[eid]["quote"])]
            risks = [name for name, pattern in RISK_PATTERNS.items() if pattern.search(text)]
            decision, reasons = "NEEDS_EVIDENCE", []
            prohibited = bool(risks and not direct_ids)
            if not ids:
                reasons.append("no evidence_id supplied")
            if missing:
                reasons.append("unknown evidence_id: " + ", ".join(missing))
            if prohibited:
                reasons.append("high-risk conclusion lacks an exact quote that directly states the conclusion")
            elif direct_ids and not missing:
                decision = "SUPPORTED"
            elif semantic_ids and not missing:
                decision = "HUMAN_REVIEW"
                reasons.append("linked quote is semantically related but does not directly contain the claim")
            elif valid_ids and not verified:
                decision = "HUMAN_REVIEW"
                reasons.append("quote cannot be verified without source_text")
            elif valid_ids and not reasons:
                reasons.append("linked evidence is unrelated to the claim")
            source_ids = sorted({evidence_index[eid]["source_id"] for eid in valid_ids})
            source_urls = [source_index[sid]["url"] for sid in source_ids]
            result = {
                "answer_id": answer["answer_id"], "claim_id": cid, "text": text,
                "decision": decision, "evidence_ids": valid_ids, "direct_evidence_ids": direct_ids,
                "source_ids": source_ids, "source_urls": source_urls, "risk_flags": risks,
                "prohibited_inference": prohibited, "reasons": reasons,
            }
            results.append(result)
            if decision == "SUPPORTED":
                rendered.append(f"{text} [{' '.join(direct_ids)} | {' '.join(source_ids)}]")
            else:
                answer_ready = False
                item = {"claim_id": cid, "reasons": reasons}
                if decision == "HUMAN_REVIEW":
                    item["action"] = "담당자가 원문과 의역의 의미 일치를 확인하세요."
                    reviews.append(item)
                else:
                    item["action"] = "직접 지지하는 정확한 공개 인용을 추가하거나 결론을 삭제하세요."
                    actions.append(item)
        if answer_ready:
            publishable.append({"answer_id": answer["answer_id"], "text": " ".join(rendered)})

    status = "NEEDS_EVIDENCE" if actions else ("HUMAN_REVIEW" if reviews else "READY")
    return {
        "status": status,
        "summary": {
            "claims": len(results),
            "supported": sum(r["decision"] == "SUPPORTED" for r in results),
            "human_review": sum(r["decision"] == "HUMAN_REVIEW" for r in results),
            "needs_evidence": sum(r["decision"] == "NEEDS_EVIDENCE" for r in results),
        },
        "claim_results": results, "publishable_answers": publishable,
        "required_actions": actions, "human_review_actions": reviews,
        "safety_note": "정확한 인용의 직접 일치만 자동 지지하며 실제 서비스 상태·원인·복구·성과를 독자적으로 판정하지 않습니다.",
    }


def run_workflow(data: object) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("draft"), str) or not data["draft"].strip():
        raise InputError("raw workflow needs a non-empty draft")
    raw_sources = _require_list(data.get("sources"), "sources")
    prepared_sources = []
    for source in raw_sources:
        copy = dict(source) if isinstance(source, dict) else source
        if not isinstance(copy, dict):
            raise InputError("each source must be an object")
        if isinstance(copy.get("source_text"), str):
            copy["content_sha256"] = hashlib.sha256(copy["source_text"].encode("utf-8")).hexdigest()
        copy["evidence"] = []
        prepared_sources.append(copy)
    _validated_sources(prepared_sources)

    claims, source_sentences = _split_sentences(data["draft"]), []
    for source in prepared_sources:
        text = source.get("source_text")
        if isinstance(text, str):
            source_sentences.append((source, text, _split_sentences(text)))
    packet_claims = []
    for claim_no, claim in enumerate(claims, 1):
        evidence_ids = []
        for source_no, (source, source_text, sentences) in enumerate(source_sentences, 1):
            candidates = []
            exact_at = source_text.find(claim)
            if exact_at >= 0:
                candidates = [(claim, exact_at)]
            else:
                for sentence in sentences:
                    if _semantic_candidate(claim, sentence):
                        candidates.append((sentence, source_text.find(sentence)))
                        break
            for quote, start in candidates:
                eid = f"EV-{source_no:02d}-{claim_no:03d}"
                source["evidence"].append({
                    "evidence_id": eid, "quote": quote,
                    "location": {"start": start, "end": start + len(quote), "unit": "utf8-character"},
                })
                evidence_ids.append(eid)
        packet_claims.append({"claim_id": f"CLM-{claim_no:03d}", "text": claim, "evidence_ids": evidence_ids})
    packet = {
        "sources": prepared_sources,
        "answers": [{"answer_id": data.get("draft_id", "DRAFT-1"), "claims": packet_claims}],
    }
    return {"evidence_packet": packet, "report": audit(packet)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        with args.input.open(encoding="utf-8") as fh:
            data = json.load(fh)
        report = run_workflow(data) if isinstance(data, dict) and "draft" in data else audit(data)
    except (OSError, json.JSONDecodeError, InputError) as exc:
        report, code = {"status": "INVALID_INPUT", "error": str(exc)}, 2
    else:
        code = 0
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
