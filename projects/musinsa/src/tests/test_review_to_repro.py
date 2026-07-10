import json
import subprocess
import sys
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from review_to_repro import SUPPORTED_JOURNEY_STAGES, InputValidationError, build_report


class ReviewToReproTests(unittest.TestCase):
    @staticmethod
    def _keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from ReviewToReproTests._keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from ReviewToReproTests._keys(child)

    def test_splits_one_review_into_independent_tickets_and_preserves_evidence(self):
        payload = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [
                {
                    "evidence_id": "APPSTORE-14280470370",
                    "source_review_id": "14280470370",
                    "source": "apple_app_store",
                    "source_url": "https://itunes.apple.com/kr/rss/customerreviews/page=1/id=1003139529/sortby=mostrecent/json",
                    "review_date": "2026-07-08T20:25:49-07:00",
                    "rating": 1,
                    "locale": "ko-KR",
                    "title": "품절 표시 오류와 전반적인 앱 성능 문제 개선 필요",
                    "text": "정상 판매 상품도 품절로 표시됩니다. 결제가 느리고 목록과 상세 화면 전환이 버벅거리며 휴대폰 발열이 심합니다.",
                    "environment": {
                        "device": "TEST-iPhone-15",
                        "os_version": "TEST-iOS-18.5",
                        "app_version": "4.81.0",
                        "provenance": "synthetic_test_context",
                    },
                }
            ],
        }

        report = build_report(payload)

        self.assertEqual(
            {ticket["observed_symptom"]["code"] for ticket in report["tickets"]},
            {
                "sold_out_mislabel",
                "checkout_latency",
                "navigation_lag",
                "device_overheating",
            },
        )
        self.assertTrue(
            all(
                ticket["evidence_ids"] == ["APPSTORE-14280470370"]
                for ticket in report["tickets"]
            )
        )

    def test_declared_journey_stage_contract_is_complete(self):
        self.assertEqual(
            set(SUPPORTED_JOURNEY_STAGES),
            {
                "search",
                "listing",
                "detail",
                "cart",
                "checkout",
                "order",
                "delivery",
                "exchange_return",
                "support",
                "notification",
                "review_submission",
                "cross_cutting_performance",
                "listing_detail",
                "unknown",
            },
        )

    def test_missing_environment_marks_each_split_ticket_needs_repro(self):
        payload = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [
                {
                    "evidence_id": "GOOGLEPLAY-f039a383-fee3-41dd-a7f8-e0e24112cfb0",
                    "source_review_id": "f039a383-fee3-41dd-a7f8-e0e24112cfb0",
                    "source": "google_play",
                    "source_url": "https://play.google.com/store/apps/details?id=com.musinsa.store&hl=ko&gl=KR",
                    "review_date": "2026-06-26T16:27:36+00:00",
                    "rating": 1,
                    "locale": "ko-KR",
                    "title": "",
                    "text": "외부 페이 결제로 나갔다 돌아오면 앱이 다시 시작됩니다. 결제는 완료되지 않았는데 프로모션은 사용 처리됩니다.",
                    "environment": {},
                }
            ],
        }

        report = build_report(payload)

        self.assertEqual(
            {ticket["observed_symptom"]["code"] for ticket in report["tickets"]},
            {
                "external_payment_return_restart",
                "payment_not_completed",
                "promotion_state_mismatch",
            },
        )
        self.assertTrue(report["tickets"])
        self.assertTrue(
            all(
                ticket["status"] == "NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION"
                for ticket in report["tickets"]
            )
        )
        self.assertTrue(
            all(
                ticket["information_gaps"]
                == ["device", "os_version", "app_version"]
                for ticket in report["tickets"]
            )
        )

    def test_rejects_review_without_evidence_id(self):
        payload = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [
                {
                    "source_review_id": "missing-evidence-id",
                    "source": "apple_app_store",
                    "source_url": "https://apps.apple.com/kr/app/id1003139529",
                    "review_date": "2026-07-10T00:00:00Z",
                    "rating": 1,
                    "locale": "ko-KR",
                    "title": "invalid",
                    "text": "결제가 느립니다.",
                    "environment": {},
                }
            ],
        }

        with self.assertRaisesRegex(InputValidationError, "evidence_id"):
            build_report(payload)

    def test_rejects_review_without_environment_object(self):
        payload = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [
                {
                    "evidence_id": "APPSTORE-NO-ENV",
                    "source_review_id": "NO-ENV",
                    "source": "apple_app_store",
                    "source_url": "https://apps.apple.com/kr/app/id1003139529",
                    "review_date": "2026-07-10T00:00:00Z",
                    "rating": 1,
                    "locale": "ko-KR",
                    "title": "invalid",
                    "text": "결제가 느립니다.",
                }
            ],
        }

        with self.assertRaisesRegex(InputValidationError, "environment is required"):
            build_report(payload)

    def test_rejects_non_public_or_unsupported_review_source(self):
        payload = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [
                {
                    "evidence_id": "PRIVATE-1",
                    "source_review_id": "1",
                    "source": "internal_customer_export",
                    "source_url": "https://example.com/not-public",
                    "review_date": "2026-07-10T00:00:00Z",
                    "rating": 1,
                    "locale": "ko-KR",
                    "title": "invalid",
                    "text": "결제가 느립니다.",
                    "environment": {},
                }
            ],
        }

        with self.assertRaisesRegex(InputValidationError, "source"):
            build_report(payload)

    def test_rejects_official_store_url_for_a_different_app(self):
        base_review = {
            "evidence_id": "WRONG-APP-1",
            "source_review_id": "1",
            "review_date": "2026-07-10T00:00:00Z",
            "rating": 1,
            "locale": "ko-KR",
            "title": "invalid",
            "text": "결제가 느립니다.",
            "environment": {},
        }
        wrong_sources = (
            {
                "source": "apple_app_store",
                "source_url": "https://apps.apple.com/kr/app/id1234567890",
            },
            {
                "source": "google_play",
                "source_url": "https://play.google.com/store/apps/details?id=com.example.other",
            },
        )

        for wrong_source in wrong_sources:
            with self.subTest(source=wrong_source["source"]):
                payload = {
                    "schema_version": "1.0",
                    "sample_scope": "public_app_review_fixture_not_user_incidence",
                    "reviews": [{**base_review, **wrong_source}],
                }
                with self.assertRaisesRegex(InputValidationError, "Musinsa app"):
                    build_report(payload)

    def test_unmatched_observation_is_preserved_for_human_triage(self):
        payload = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [
                {
                    "evidence_id": "APPSTORE-UNKNOWN",
                    "source_review_id": "UNKNOWN",
                    "source": "apple_app_store",
                    "source_url": "https://apps.apple.com/kr/app/id1003139529",
                    "review_date": "2026-07-10T00:00:00Z",
                    "rating": 2,
                    "locale": "ko-KR",
                    "title": "불편",
                    "text": "사용하기 불편합니다.",
                    "environment": {
                        "device": "TEST-iPhone-15",
                        "os_version": "TEST-iOS-18.5",
                        "app_version": "4.81.0",
                        "provenance": "synthetic_test_context",
                    },
                }
            ],
        }

        report = build_report(payload)

        self.assertEqual(len(report["tickets"]), 1)
        ticket = report["tickets"][0]
        self.assertEqual(ticket["journey_stage"], "unknown")
        self.assertEqual(ticket["observed_symptom"]["code"], "unclassified_observation")
        self.assertEqual(
            ticket["status"], "NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION"
        )
        self.assertIn("observable_symptom", ticket["information_gaps"])
        self.assertIn("APPSTORE-UNKNOWN", ticket["evidence_ids"])
        self.assertFalse(report["regression_tests"][0]["automation_candidate"])

    def test_output_preserves_source_references_and_never_generates_root_cause(self):
        payload = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [
                {
                    "evidence_id": "APPSTORE-14280263542",
                    "source_review_id": "14280263542",
                    "source": "apple_app_store",
                    "source_url": "https://itunes.apple.com/kr/rss/customerreviews/page=1/id=1003139529/sortby=mostrecent/json",
                    "review_date": "2026-07-08T19:08:19-07:00",
                    "rating": 2,
                    "locale": "ko-KR",
                    "title": "상세 페이지에서 목록으로 돌아가면",
                    "text": "상세에서 목록으로 돌아가면 목록이 다시 로드되고 보던 스크롤 위치를 잃습니다. 서버 문제라고 생각합니다.",
                    "environment": {
                        "device": "TEST-iPhone-15",
                        "os_version": "TEST-iOS-18.5",
                        "app_version": "4.81.0",
                        "provenance": "synthetic_test_context",
                    },
                }
            ],
        }

        report = build_report(payload)

        self.assertEqual(report["input_evidence_ids"], ["APPSTORE-14280263542"])
        self.assertEqual(len(report["tickets"]), 1)
        ticket = report["tickets"][0]
        self.assertEqual(ticket["source_review_ids"], ["14280263542"])
        self.assertEqual(
            ticket["evidence_refs"][0]["source_url"], payload["reviews"][0]["source_url"]
        )
        self.assertEqual(len(report["regression_tests"]), 1)
        self.assertEqual(
            report["regression_tests"][0]["evidence_ids"],
            ["APPSTORE-14280263542"],
        )
        self.assertNotIn("root_cause", set(self._keys(report)))
        self.assertNotIn("서버", ticket["observed_symptom"]["statement"])

    def test_stable_fields_do_not_change_when_review_order_changes(self):
        base_review = {
            "source": "apple_app_store",
            "source_url": "https://itunes.apple.com/kr/rss/customerreviews/page=1/id=1003139529/sortby=mostrecent/json",
            "review_date": "2026-07-08T20:25:49-07:00",
            "rating": 1,
            "locale": "ko-KR",
            "title": "",
            "environment": {
                "device": "TEST-iPhone-15",
                "os_version": "TEST-iOS-18.5",
                "app_version": "4.81.0",
                "provenance": "synthetic_test_context",
            },
        }
        first = {
            **base_review,
            "evidence_id": "APPSTORE-A",
            "source_review_id": "A",
            "text": "결제가 느립니다.",
        }
        second = {
            **base_review,
            "evidence_id": "APPSTORE-B",
            "source_review_id": "B",
            "text": "휴대폰 발열이 심합니다.",
        }
        forward = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [first, second],
        }
        reverse = {**forward, "reviews": [second, first]}

        forward_report = build_report(forward)
        reverse_report = build_report(reverse)

        self.assertRegex(forward_report["stable_fields_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            forward_report["stable_fields_sha256"],
            reverse_report["stable_fields_sha256"],
        )
        self.assertEqual(forward_report["tickets"], reverse_report["tickets"])
        self.assertEqual(
            forward_report["regression_tests"], reverse_report["regression_tests"]
        )

    def test_cli_rejects_invalid_fixture_with_machine_readable_error(self):
        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "review_to_repro.py"),
                str(PLUGIN_ROOT / "fixtures" / "invalid.json"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(result.returncode, 2)
        error = json.loads(result.stderr)
        self.assertEqual(error["error"], "INVALID_INPUT")
        self.assertIn("evidence_id", error["message"])

    def test_cli_normal_fixture_emits_testable_summary(self):
        result = subprocess.run(
            [
                sys.executable,
                str(PLUGIN_ROOT / "scripts" / "review_to_repro.py"),
                str(PLUGIN_ROOT / "fixtures" / "normal.json"),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(
            report["summary"],
            {
                "input_reviews": 1,
                "input_evidence_ids": 1,
                "tickets": 4,
                "regression_tests": 4,
                "status_counts": {
                    "READY_FOR_REPRO": 0,
                    "TEST_SCENARIO_ONLY": 4,
                    "NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION": 0,
                },
                "evidence_preservation_rate": 1.0,
            },
        )

    def test_human_judgment_and_environment_provenance_are_explicit(self):
        payload = json.loads(
            (PLUGIN_ROOT / "fixtures" / "normal.json").read_text(encoding="utf-8")
        )

        report = build_report(payload)

        expected_human_decisions = [
            "severity",
            "business_priority",
            "duplicate_confirmation",
            "actual_reproduction_result",
            "policy_violation",
        ]
        for ticket in report["tickets"]:
            self.assertEqual(ticket["human_decisions"], expected_human_decisions)
            self.assertEqual(
                ticket["environment"]["provenance"]["device"],
                "synthetic_test_context",
            )
            self.assertEqual(ticket["status"], "TEST_SCENARIO_ONLY")
            self.assertTrue(ticket["reproduction_draft"]["human_validation_required"])
            self.assertEqual(ticket["cause_handling"], "NOT_GENERATED_FROM_REVIEW")
        for regression_test in report["regression_tests"]:
            self.assertIsNone(regression_test["automation_candidate"])
            self.assertEqual(
                regression_test["automation_assessment"],
                "HUMAN_ASSESSMENT_REQUIRED",
            )

    def test_every_input_evidence_id_has_ticket_and_regression_traceability(self):
        normal = json.loads(
            (PLUGIN_ROOT / "fixtures" / "normal.json").read_text(encoding="utf-8")
        )
        sparse = json.loads(
            (PLUGIN_ROOT / "fixtures" / "sparse.json").read_text(encoding="utf-8")
        )
        payload = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [*normal["reviews"], *sparse["reviews"]],
        }

        report = build_report(payload)

        self.assertEqual(
            set(report["evidence_traceability"]),
            {
                "APPSTORE-14280470370",
                "GOOGLEPLAY-f039a383-fee3-41dd-a7f8-e0e24112cfb0",
            },
        )
        for trace in report["evidence_traceability"].values():
            self.assertTrue(trace["ticket_ids"])
            self.assertTrue(trace["regression_test_ids"])
            self.assertTrue(trace["source_review_id"])
        self.assertEqual(report["summary"]["evidence_preservation_rate"], 1.0)

    def test_synthetic_environment_can_never_be_ready_for_repro(self):
        payload = json.loads(
            (PLUGIN_ROOT / "fixtures" / "normal.json").read_text(encoding="utf-8")
        )

        report = build_report(payload)

        self.assertTrue(report["tickets"])
        self.assertTrue(
            all(ticket["status"] == "TEST_SCENARIO_ONLY" for ticket in report["tickets"])
        )
        self.assertEqual(report["summary"]["status_counts"]["READY_FOR_REPRO"], 0)

    def test_ready_requires_trusted_provenance_for_each_environment_field(self):
        payload = json.loads(
            (PLUGIN_ROOT / "fixtures" / "normal.json").read_text(encoding="utf-8")
        )
        environment = payload["reviews"][0]["environment"]
        environment["provenance"] = "review_reported"

        aggregate_report = build_report(payload)

        self.assertTrue(
            all(
                ticket["status"] == "NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION"
                for ticket in aggregate_report["tickets"]
            )
        )

        environment["provenance"] = {
            "device": "review_reported",
            "os_version": "verified_test_run",
            "app_version": "store_metadata",
        }
        per_field_report = build_report(payload)

        self.assertTrue(
            all(
                ticket["status"] == "READY_FOR_REPRO"
                for ticket in per_field_report["tickets"]
            )
        )

    def test_matched_evidence_is_exact_substring_with_offsets_and_hash(self):
        payload = json.loads(
            (PLUGIN_ROOT / "fixtures" / "normal.json").read_text(encoding="utf-8")
        )
        source_text = payload["reviews"][0]["raw_review_text"]
        expected_hash = __import__("hashlib").sha256(source_text.encode("utf-8")).hexdigest()

        report = build_report(payload)

        for ticket in report["tickets"]:
            matched = ticket["matched_evidence"]
            self.assertEqual(
                matched["text"],
                source_text[matched["start_offset"] : matched["end_offset"]],
            )
            self.assertEqual(matched["raw_text_sha256"], expected_hash)
            self.assertEqual(matched["evidence_id"], "APPSTORE-14280470370")
            self.assertEqual(matched["source_review_id"], "14280470370")
            self.assertEqual(matched["text_basis"], "raw_review_text")

    def test_each_symptom_has_distinct_reproduction_steps(self):
        normal = json.loads(
            (PLUGIN_ROOT / "fixtures" / "normal.json").read_text(encoding="utf-8")
        )
        sparse = json.loads(
            (PLUGIN_ROOT / "fixtures" / "sparse.json").read_text(encoding="utf-8")
        )
        payload = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [*normal["reviews"], *sparse["reviews"]],
        }

        report = build_report(payload)
        steps_by_symptom = {
            ticket["observed_symptom"]["code"]: tuple(
                ticket["reproduction_draft"]["steps"]
            )
            for ticket in report["tickets"]
        }

        self.assertEqual(len(steps_by_symptom), 7)
        self.assertEqual(len(set(steps_by_symptom.values())), 7)
        self.assertIn("판매 가능 상태의 대상 상품", steps_by_symptom["sold_out_mislabel"][0])
        self.assertIn("결제 시작 시각", " ".join(steps_by_symptom["checkout_latency"]))
        self.assertIn("목록→상세→뒤로", " ".join(steps_by_symptom["navigation_lag"]))
        self.assertIn("기준 상태", " ".join(steps_by_symptom["device_overheating"]))
        self.assertIn("외부 결제", " ".join(steps_by_symptom["external_payment_return_restart"]))
        self.assertIn("주문·결제 상태", " ".join(steps_by_symptom["payment_not_completed"]))
        self.assertIn("프로모션 사용 상태", " ".join(steps_by_symptom["promotion_state_mismatch"]))

    def test_each_symptom_has_specific_oracle_contract(self):
        payload = json.loads(
            (PLUGIN_ROOT / "fixtures" / "normal.json").read_text(encoding="utf-8")
        )

        report = build_report(payload)
        oracle_types = {
            test["symptom_code"]: test["oracle_type"]
            for test in report["regression_tests"]
        }

        self.assertEqual(len(set(oracle_types.values())), len(oracle_types))
        for test in report["regression_tests"]:
            self.assertTrue(test["required_observations"])
            self.assertTrue(test["human_defined_thresholds"])
            self.assertNotIn("관찰 증상이 발생하지 않고", json.dumps(test, ensure_ascii=False))

    def test_normalized_observation_is_not_presented_as_raw_review_text(self):
        payload = {
            "schema_version": "1.0",
            "sample_scope": "public_app_review_fixture_not_user_incidence",
            "reviews": [
                {
                    "evidence_id": "APPSTORE-NORMALIZED",
                    "source_review_id": "NORMALIZED",
                    "source": "apple_app_store",
                    "source_url": "https://apps.apple.com/kr/app/id1003139529",
                    "review_date": "2026-07-10T00:00:00Z",
                    "rating": 1,
                    "locale": "ko-KR",
                    "title": "normalized",
                    "normalized_observation": "결제가 느립니다.",
                    "text": "결제가 느립니다.",
                    "text_provenance": "normalized_observation_from_public_review",
                    "normalization_method": "manual_semantic_rewrite",
                    "source_raw_text_sha256": "a" * 64,
                    "environment": {},
                }
            ],
        }

        report = build_report(payload)
        ticket = report["tickets"][0]
        text_record = ticket["evidence_refs"][0]["review_text"]

        self.assertEqual(ticket["matched_evidence"]["text_basis"], "normalized_observation")
        self.assertFalse(ticket["matched_evidence"]["is_raw_review_text"])
        self.assertNotIn("raw_review_text", text_record)
        self.assertEqual(text_record["normalized_observation"], "결제가 느립니다.")
        self.assertEqual(text_record["normalization_method"], "manual_semantic_rewrite")
        self.assertEqual(text_record["source_raw_text_sha256"], "a" * 64)


if __name__ == "__main__":
    unittest.main()
