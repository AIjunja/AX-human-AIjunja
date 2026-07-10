"""Deterministic evidence gate for customer-support answer drafts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

RISK_PATTERNS = {
    "service_wide_outage": re.compile(r"(서비스|시스템|전체).{0,8}(전체\s*)?(장애|먹통)"),
    "root_cause": re.compile(r"(원인은|원인으로|때문에 발생|장애 원인)"),
    "recovery_complete": re.compile(r"(복구\s*완료|완전히\s*복구|정상화\s*완료)"),
    "performance_claim": re.compile(r"(성과|해결률|응답률|전환율).{0,12}(향상|증가|개선|상승)"),
}


class InputError(ValueError):
    pass


def _public_https(url: object) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and bool(host) and host not in {"localhost", "127.0.0.1", "::1"}


def _require_list(value: object, name: str) -> list:
    if not isinstance(value, list) or not value:
        raise InputError(f"{name} must be a non-empty array")
    return value


def audit(data: object) -> dict:
    if not isinstance(data, dict):
        raise InputError("root must be an object")
    sources = _require_list(data.get("sources"), "sources")
    answers = _require_list(data.get("answers"), "answers")

    evidence_index: dict[str, dict] = {}
    source_index: dict[str, dict] = {}
    for source in sources:
        if not isinstance(source, dict):
            raise InputError("each source must be an object")
        sid, url, title = source.get("source_id"), source.get("url"), source.get("title")
        if not all(isinstance(v, str) and v.strip() for v in (sid, title)):
            raise InputError("source_id and title are required strings")
        if sid in source_index:
            raise InputError(f"duplicate source_id: {sid}")
        if not _public_https(url):
            raise InputError(f"source {sid} must use a public HTTPS URL")
        source_index[sid] = {"title": title, "url": url}
        for ev in _require_list(source.get("evidence"), f"source {sid}.evidence"):
            if not isinstance(ev, dict):
                raise InputError("each evidence must be an object")
            eid, text = ev.get("evidence_id"), ev.get("text")
            if not all(isinstance(v, str) and v.strip() for v in (eid, text)):
                raise InputError("evidence_id and text are required strings")
            if eid in evidence_index:
                raise InputError(f"duplicate evidence_id: {eid}")
            evidence_index[eid] = {"source_id": sid, "text": text}

    results, publishable, actions = [], [], []
    seen_claims: set[str] = set()
    for answer in answers:
        if not isinstance(answer, dict) or not isinstance(answer.get("answer_id"), str):
            raise InputError("each answer needs answer_id")
        claims = _require_list(answer.get("claims"), f"answer {answer.get('answer_id')}.claims")
        rendered = []
        answer_ready = True
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
            risks = [name for name, pattern in RISK_PATTERNS.items() if pattern.search(text)]
            explicit = []
            if ids:
                combined = " ".join(evidence_index[eid]["text"] for eid in ids if eid in evidence_index)
                explicit = [name for name in risks if RISK_PATTERNS[name].search(combined)]
            prohibited = bool(set(risks) - set(explicit))
            decision = "SUPPORTED"
            reasons = []
            if not ids:
                decision = "NEEDS_EVIDENCE"
                reasons.append("no evidence_id supplied")
            if missing:
                decision = "NEEDS_EVIDENCE"
                reasons.append("unknown evidence_id: " + ", ".join(missing))
            if prohibited:
                decision = "NEEDS_EVIDENCE"
                reasons.append("high-risk conclusion is not explicit in linked evidence")
            valid_ids = [eid for eid in ids if eid in evidence_index]
            source_ids = sorted({evidence_index[eid]["source_id"] for eid in valid_ids})
            source_urls = [source_index[sid]["url"] for sid in source_ids]
            result = {
                "answer_id": answer["answer_id"], "claim_id": cid, "text": text,
                "decision": decision, "evidence_ids": valid_ids, "source_ids": source_ids,
                "source_urls": source_urls, "risk_flags": risks,
                "prohibited_inference": prohibited, "reasons": reasons,
            }
            results.append(result)
            if decision == "SUPPORTED":
                rendered.append(f"{text} [{' '.join(valid_ids)} | {' '.join(source_ids)}]")
            else:
                answer_ready = False
                actions.append({"claim_id": cid, "action": "공개 근거를 추가하거나 해당 결론을 삭제하세요.", "reasons": reasons})
        if answer_ready:
            publishable.append({"answer_id": answer["answer_id"], "text": " ".join(rendered)})

    return {
        "status": "READY" if not actions else "NEEDS_EVIDENCE",
        "summary": {"claims": len(results), "supported": sum(r["decision"] == "SUPPORTED" for r in results), "blocked": len(actions)},
        "claim_results": results, "publishable_answers": publishable,
        "required_actions": actions,
        "safety_note": "이 도구는 제공된 공개 근거의 연결과 위험 문구를 검사하며 실제 서비스 상태·원인·복구·성과를 독자적으로 판정하지 않습니다.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        with args.input.open(encoding="utf-8") as fh:
            report = audit(json.load(fh))
    except (OSError, json.JSONDecodeError, InputError) as exc:
        report = {"status": "INVALID_INPUT", "error": str(exc)}
        code = 2
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
