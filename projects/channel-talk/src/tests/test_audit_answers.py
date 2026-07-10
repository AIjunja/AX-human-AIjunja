import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audit_answers", ROOT / "scripts" / "audit_answers.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class AuditAnswersTest(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))

    def test_valid_is_ready_and_preserves_ids(self):
        out = MODULE.audit(self.load("valid.json"))
        self.assertEqual("READY", out["status"])
        self.assertEqual(["EV-ALF-01"], out["claim_results"][0]["evidence_ids"])
        self.assertEqual(["SRC-CH-ALF-2025"], out["claim_results"][0]["source_ids"])
        self.assertIn("https://", out["claim_results"][0]["source_urls"][0])

    def test_missing_evidence_blocks_unsupported_outage_claim(self):
        out = MODULE.audit(self.load("missing-evidence.json"))
        self.assertEqual("NEEDS_EVIDENCE", out["status"])
        claim = out["claim_results"][0]
        self.assertTrue(claim["prohibited_inference"])
        self.assertIn("service_wide_outage", claim["risk_flags"])
        self.assertIn("root_cause", claim["risk_flags"])
        self.assertIn("recovery_complete", claim["risk_flags"])
        self.assertEqual([], out["publishable_answers"])

    def test_invalid_fixture_exits_two_without_traceback(self):
        p = subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_answers.py"), str(ROOT / "fixtures" / "invalid.json")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(2, p.returncode)
        payload = json.loads(p.stdout)
        self.assertEqual("INVALID_INPUT", payload["status"])
        self.assertNotIn("Traceback", p.stderr)

    def test_unknown_evidence_id_is_not_preserved_as_valid(self):
        data = self.load("valid.json")
        data["answers"][0]["claims"][0]["evidence_ids"] = ["EV-NOT-FOUND"]
        out = MODULE.audit(data)
        self.assertEqual("NEEDS_EVIDENCE", out["status"])
        self.assertEqual([], out["claim_results"][0]["evidence_ids"])

    def packet(self, claim_text, quote, start, end):
        source_text = "안내: " + quote + " 추가 문장입니다."
        return {
            "sources": [{
                "source_id": "SRC-1", "title": "공식 안내",
                "url": "https://docs.example.com/guide",
                "retrieved_at": "2026-07-10T13:00:00Z",
                "source_text": source_text,
                "evidence": [{
                    "evidence_id": "EV-1", "quote": quote,
                    "location": {"start": start, "end": end},
                }],
            }],
            "answers": [{"answer_id": "ANS-1", "claims": [{
                "claim_id": "CLM-1", "text": claim_text,
                "evidence_ids": ["EV-1"],
            }]}],
        }

    def test_raw_draft_workflow_splits_claims_and_builds_evidence_packet(self):
        source_text = "AI 어시스턴트는 FAQ를 기반으로 답변합니다. 출처가 없으면 공식 문서로 확인하세요."
        out = MODULE.run_workflow({
            "draft_id": "DRAFT-1",
            "draft": "AI 어시스턴트는 FAQ를 기반으로 답변합니다. 출처가 없으면 공식 문서로 확인하세요.",
            "sources": [{
                "source_id": "SRC-1", "title": "공식 안내",
                "url": "https://channel.io/kr/blog/example",
                "retrieved_at": "2026-07-10T13:00:00Z",
                "source_text": source_text,
            }],
        })
        self.assertEqual(2, len(out["evidence_packet"]["answers"][0]["claims"]))
        self.assertEqual("READY", out["report"]["status"])
        self.assertTrue(all(x["decision"] == "SUPPORTED" for x in out["report"]["claim_results"]))
        first = out["evidence_packet"]["sources"][0]["evidence"][0]
        self.assertEqual(first["quote"], source_text[first["location"]["start"]:first["location"]["end"]])
        self.assertRegex(out["evidence_packet"]["sources"][0]["content_sha256"], r"^[0-9a-f]{64}$")

    def test_unrelated_evidence_does_not_support_general_claim(self):
        quote = "운영 시간은 평일 오전 9시부터 오후 6시까지입니다."
        data = self.packet("환불은 언제나 즉시 완료됩니다.", quote, 4, 4 + len(quote))
        out = MODULE.audit(data)
        self.assertEqual("NEEDS_EVIDENCE", out["claim_results"][0]["decision"])

    def test_semantic_paraphrase_requires_human_review(self):
        quote = "출처가 표시되지 않은 경우 공식 문서를 통해 한 번 더 체크해 주세요."
        data = self.packet("출처 없는 답변은 공식 가이드로 추가 확인해야 합니다.", quote, 4, 4 + len(quote))
        out = MODULE.audit(data)
        self.assertEqual("HUMAN_REVIEW", out["claim_results"][0]["decision"])
        self.assertEqual("HUMAN_REVIEW", out["status"])

    def test_scattered_risk_words_do_not_support_outage_conclusion(self):
        quote = "서비스 안내입니다. 장애인 접근성을 지원합니다. 원인은 별도 문단의 일반 용어이며 복구 완료 체크리스트가 있습니다."
        data = self.packet("서비스 전체 장애의 원인은 인증 서버이며 복구 완료되었습니다.", quote, 4, 4 + len(quote))
        out = MODULE.audit(data)
        claim = out["claim_results"][0]
        self.assertEqual("NEEDS_EVIDENCE", claim["decision"])
        self.assertTrue(claim["prohibited_inference"])

    def test_quote_location_must_match_source_text(self):
        quote = "공식 인용입니다."
        data = self.packet(quote, quote, 0, len(quote))
        with self.assertRaisesRegex(MODULE.InputError, "quote location"):
            MODULE.audit(data)

    def test_non_public_ip_urls_are_rejected(self):
        blocked = [
            "https://127.0.0.1/a", "https://10.0.0.1/a", "https://172.16.0.1/a",
            "https://192.168.1.1/a", "https://169.254.1.1/a", "https://224.0.0.1/a",
            "https://240.0.0.1/a", "https://[::1]/a", "https://[fe80::1]/a",
            "https://192.0.2.1/a",
        ]
        for url in blocked:
            with self.subTest(url=url):
                self.assertFalse(MODULE._public_https(url))


if __name__ == "__main__":
    unittest.main()
