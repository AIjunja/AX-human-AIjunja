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


if __name__ == "__main__":
    unittest.main()
