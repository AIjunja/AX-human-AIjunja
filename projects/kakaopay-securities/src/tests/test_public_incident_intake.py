from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = SRC_ROOT / "scripts"
FIXTURES_ROOT = SRC_ROOT / "fixtures"
sys.path.insert(0, str(SCRIPTS_ROOT))

from build_incident_intake import (  # noqa: E402
    FORBIDDEN_OUTPUT_KEYS,
    InputValidationError,
    PROHIBITED_CONCLUSIONS,
    build_packet,
)


EXPECTED_PROOF = (
    "KPS_PUBLIC_INCIDENT_INTAKE_OK:v1|case=KPS-PUBLIC-2026-06-30-A|"
    "status=READY_FOR_HUMAN_TRIAGE|evidence=4|reports=2|official=2|"
    "preserved=100%|forbidden=PASS"
)


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


def clone(value: dict) -> dict:
    return json.loads(json.dumps(value, ensure_ascii=False))


def nested_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(nested_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(nested_keys(child))
    return keys


def referenced_evidence_ids(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "evidence_ids" and isinstance(child, list):
                found.update(str(item) for item in child)
            else:
                found.update(referenced_evidence_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(referenced_evidence_ids(child))
    return found


class PublicIncidentIntakeTests(unittest.TestCase):
    def test_normal_fixture_is_ready_and_preserves_every_evidence_id(self) -> None:
        payload = load_fixture("normal.json")
        result = build_packet(payload)
        self.assertEqual(result["workflow_status"], "READY_FOR_HUMAN_TRIAGE")
        expected = {
            row["evidence_id"]
            for key in ("public_reports", "official_sources")
            for row in payload[key]
        }
        actual = {row["evidence_id"] for row in result["evidence_registry"]}
        self.assertEqual(actual, expected)
        self.assertEqual(result["safety_review"]["evidence_id_preservation_percent"], 100)

    def test_normal_fixture_has_stable_classification_and_source_counts(self) -> None:
        result = build_packet(load_fixture("normal.json"))
        self.assertEqual(result["event_classification"], "PUBLIC_REPORT_CLUSTER")
        self.assertEqual(result["source_coverage"]["public_report_count"], 2)
        self.assertEqual(result["source_coverage"]["official_source_count"], 2)
        self.assertEqual(
            result["official_corroboration"]["status"],
            "OFFICIAL_SOURCE_IN_WINDOW",
        )
        self.assertEqual(result["temporal_association"]["candidate_report_count"], 2)
        self.assertEqual(
            result["temporal_association"]["unresolved_report_ids"],
            ["GP-1DFE18BB", "GP-9B529133"],
        )

    def test_public_standard_alone_cannot_corroborate_company_incident(self) -> None:
        payload = load_fixture("normal.json")
        payload["official_sources"] = [
            {
                "evidence_id": "PUBLIC-STANDARD-1",
                "source_record_id": "law-1",
                "source_url": "https://law.go.kr/example",
                "source_type": "public_standard",
                "published_at": "2026-06-30T07:10:00+09:00",
                "captured_at": "2026-07-10T21:30:00+09:00",
                "text": "공개 업계 기준",
            }
        ]

        result = build_packet(payload)

        self.assertEqual(result["workflow_status"], "NEEDS_MORE_PUBLIC_INFORMATION")
        self.assertEqual(
            result["official_corroboration"]["status"],
            "NO_MATCHING_OFFICIAL_SOURCE",
        )
        self.assertEqual(
            result["temporal_association"]["exact_window_official_source_ids"],
            [],
        )

    def test_normal_fixture_emits_deterministic_proof_line(self) -> None:
        result = build_packet(load_fixture("normal.json"))
        self.assertEqual(result["proof_line"], EXPECTED_PROOF)
        self.assertEqual(result, build_packet(load_fixture("normal.json")))

    def test_normal_fixture_extracts_only_observation_codes(self) -> None:
        result = build_packet(load_fixture("normal.json"))
        codes = {item["code"] for item in result["reported_signals"]}
        self.assertIn("SECURITIES_SURFACE", codes)
        self.assertIn("UNAVAILABLE", codes)
        self.assertNotIn("ROOT_CAUSE", codes)

    def test_input_text_is_hashed_but_not_repeated_in_output(self) -> None:
        payload = load_fixture("normal.json")
        result = build_packet(payload)
        serialized = json.dumps(result, ensure_ascii=False)
        for row in payload["public_reports"] + payload["official_sources"]:
            self.assertNotIn(row["text"], serialized)
            registry = next(
                item
                for item in result["evidence_registry"]
                if item["evidence_id"] == row["evidence_id"]
            )
            self.assertEqual(
                registry["content_sha256"],
                hashlib.sha256(row["text"].encode("utf-8")).hexdigest(),
            )

    def test_every_derived_evidence_reference_exists_in_registry(self) -> None:
        result = build_packet(load_fixture("normal.json"))
        registry_ids = {item["evidence_id"] for item in result["evidence_registry"]}
        self.assertTrue(referenced_evidence_ids(result))
        self.assertLessEqual(referenced_evidence_ids(result), registry_ids)

    def test_every_source_record_id_is_preserved(self) -> None:
        payload = load_fixture("normal.json")
        result = build_packet(payload)
        expected = {
            row["source_record_id"]
            for key in ("public_reports", "official_sources")
            for row in payload[key]
        }
        actual = {row["source_record_id"] for row in result["evidence_registry"]}
        self.assertEqual(actual, expected)

    def test_insufficient_fixture_succeeds_without_inventing_facts(self) -> None:
        result = build_packet(load_fixture("insufficient.json"))
        self.assertEqual(result["workflow_status"], "NEEDS_MORE_PUBLIC_INFORMATION")
        self.assertEqual(
            result["official_corroboration"]["status"],
            "NO_MATCHING_OFFICIAL_SOURCE",
        )
        self.assertTrue(result["missing_information"])
        missing = result["missing_information"][0]["fields"]
        self.assertIn("app_version", missing)
        self.assertIn("device_os", missing)
        self.assertIn("reproduction_steps", missing)

    def test_invalid_fixture_reports_duplicate_sensitive_and_https_errors(self) -> None:
        with self.assertRaises(InputValidationError) as caught:
            build_packet(load_fixture("invalid.json"))
        self.assertIn("DUPLICATE_EVIDENCE_ID", caught.exception.codes)
        self.assertIn("SENSITIVE_FIELD_FORBIDDEN", caught.exception.codes)
        self.assertIn("SOURCE_URL_NOT_HTTPS", caught.exception.codes)

    def test_sensitive_pattern_in_public_text_is_rejected(self) -> None:
        payload = clone(load_fixture("insufficient.json"))
        payload["public_reports"][0]["text"] += " contact@example.com"
        with self.assertRaises(InputValidationError) as caught:
            build_packet(payload)
        self.assertIn("SENSITIVE_TEXT_DETECTED", caught.exception.codes)

    def test_sensitive_patterns_in_optional_fields_are_rejected(self) -> None:
        payload = clone(load_fixture("insufficient.json"))
        payload["public_reports"][0]["reproduction_steps"] = [
            "문의 전화 010-1234-5678로 재현"
        ]
        with self.assertRaises(InputValidationError) as caught:
            build_packet(payload)
        self.assertIn("SENSITIVE_TEXT_DETECTED", caught.exception.codes)

    def test_official_source_url_must_match_its_declared_source_type(self) -> None:
        payload = clone(load_fixture("normal.json"))
        payload["official_sources"][0]["source_url"] = "https://example.com/fake?id=7314"
        with self.assertRaises(InputValidationError) as caught:
            build_packet(payload)
        self.assertIn("UNTRUSTED_SOURCE_URL", caught.exception.codes)

    def test_duplicate_public_content_cannot_fill_ready_threshold(self) -> None:
        payload = clone(load_fixture("normal.json"))
        payload["public_reports"][1]["text"] = payload["public_reports"][0]["text"]
        with self.assertRaises(InputValidationError) as caught:
            build_packet(payload)
        self.assertIn("DUPLICATE_SOURCE_CONTENT", caught.exception.codes)

    def test_old_public_reports_do_not_qualify_for_current_window(self) -> None:
        payload = clone(load_fixture("normal.json"))
        for report in payload["public_reports"]:
            report["published_at"] = "2024-06-30"
        result = build_packet(payload)
        self.assertEqual(result["workflow_status"], "NEEDS_MORE_PUBLIC_INFORMATION")
        self.assertEqual(result["temporal_association"]["candidate_report_count"], 0)
        self.assertEqual(
            set(result["temporal_association"]["outside_window_report_ids"]),
            {"GP-1DFE18BB", "GP-9B529133"},
        )

    def test_unrelated_public_reports_do_not_qualify_for_ready_status(self) -> None:
        payload = clone(load_fixture("normal.json"))
        payload["public_reports"][0]["text"] = "송금 화면 접속이 안 됩니다"
        payload["public_reports"][1]["text"] = "결제 화면이 열리지 않습니다"
        result = build_packet(payload)
        self.assertEqual(result["workflow_status"], "NEEDS_MORE_PUBLIC_INFORMATION")
        self.assertEqual(result["temporal_association"]["candidate_report_count"], 0)
        self.assertEqual(
            set(result["temporal_association"]["topic_irrelevant_report_ids"]),
            {"GP-1DFE18BB", "GP-9B529133"},
        )

    def test_date_only_official_source_does_not_match_narrow_window(self) -> None:
        payload = clone(load_fixture("normal.json"))
        for source in payload["official_sources"]:
            source["published_at"] = "2026-06-30"
        result = build_packet(payload)
        self.assertEqual(result["workflow_status"], "NEEDS_MORE_PUBLIC_INFORMATION")
        self.assertEqual(
            result["official_corroboration"]["status"],
            "NO_MATCHING_OFFICIAL_SOURCE",
        )
        self.assertEqual(
            set(result["temporal_association"]["date_only_official_source_ids"]),
            {"KPS-NOTICE-7314", "KPS-NOTICE-7315"},
        )

    def test_optional_reproduction_fields_require_valid_types(self) -> None:
        payload = clone(load_fixture("insufficient.json"))
        report = payload["public_reports"][0]
        report["platform"] = {"name": "ios"}
        report["exact_occurred_at"] = "sometime"
        report["expected_result"] = 42
        with self.assertRaises(InputValidationError) as caught:
            build_packet(payload)
        self.assertIn("PLATFORM_INVALID", caught.exception.codes)
        self.assertIn("EXACT_OCCURRED_AT_INVALID", caught.exception.codes)
        self.assertIn("OPTIONAL_TEXT_INVALID", caught.exception.codes)

    def test_reversed_observed_window_is_rejected(self) -> None:
        payload = clone(load_fixture("insufficient.json"))
        payload["observed_window"]["start"], payload["observed_window"]["end"] = (
            payload["observed_window"]["end"],
            payload["observed_window"]["start"],
        )
        with self.assertRaises(InputValidationError) as caught:
            build_packet(payload)
        self.assertIn("OBSERVED_WINDOW_REVERSED", caught.exception.codes)

    def test_prohibited_conclusions_are_all_not_assessed(self) -> None:
        result = build_packet(load_fixture("normal.json"))
        self.assertEqual(
            {item["code"] for item in result["prohibited_conclusions"]},
            set(PROHIBITED_CONCLUSIONS),
        )
        self.assertTrue(
            all(item["status"] == "NOT_ASSESSED" for item in result["prohibited_conclusions"])
        )
        self.assertFalse(nested_keys(result) & set(FORBIDDEN_OUTPUT_KEYS))
        self.assertEqual(result["safety_review"]["result"], "PASS")

    def test_cli_normal_proof_only_matches_expected(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(SCRIPTS_ROOT / "build_incident_intake.py"),
                str(FIXTURES_ROOT / "normal.json"),
                "--proof-only",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), EXPECTED_PROOF)
        self.assertEqual(completed.stderr, "")

    def test_cli_invalid_returns_structured_error_and_exit_two(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(SCRIPTS_ROOT / "build_incident_intake.py"),
                str(FIXTURES_ROOT / "invalid.json"),
                "--compact",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        error = json.loads(completed.stderr)
        self.assertFalse(error["ok"])
        self.assertEqual(error["error"], "INPUT_VALIDATION_FAILED")
        self.assertEqual(completed.stdout, "")

    def test_cli_non_utf8_input_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "not-utf8.json"
            input_path.write_bytes(b"{\xff}")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-X",
                    "utf8",
                    str(SCRIPTS_ROOT / "build_incident_intake.py"),
                    str(input_path),
                    "--compact",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
        self.assertEqual(completed.returncode, 2)
        error = json.loads(completed.stderr)
        self.assertEqual(error["error"], "INPUT_FILE_INVALID")
        self.assertEqual(completed.stdout, "")


if __name__ == "__main__":
    unittest.main()
