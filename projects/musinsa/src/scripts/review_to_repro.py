from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


SUPPORTED_JOURNEY_STAGES = (
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
)


SYMPTOM_RULES = (
    ("search", "search_result_missing", ("검색 결과가 없", "검색이 안", "검색되지 않")),
    ("detail", "sold_out_mislabel", ("품절로 표시",)),
    ("detail", "detail_image_missing", ("상세 이미지가 안", "이미지가 깨", "이미지 안 보여")),
    ("cart", "cart_item_missing", ("장바구니에서 사라", "장바구니가 비어")),
    ("checkout", "checkout_latency", ("결제가 느", "결제 과정은 지나치게 느")),
    (
        "checkout",
        "external_payment_return_restart",
        ("돌아오면 앱이 다시 시작", "나갔다오면 튕겨서", "나갔다 돌아오면 앱이 다시 시작"),
    ),
    ("checkout", "payment_not_completed", ("결제는 완료되지", "결제는 안되어", "결제가 완료되지")),
    ("checkout", "promotion_state_mismatch", ("프로모션은 사용 처리", "프로모션 이미 썼다")),
    ("checkout", "checkout_blank_screen", ("구매하기 누르면 흰", "결제 화면이 흰")),
    ("order", "order_history_missing", ("주문 내역이 없", "주문 이력이 없")),
    ("delivery", "delivery_delay", ("출고가 지연", "배송이 지연", "예정일이 지나")),
    (
        "exchange_return",
        "exchange_return_status_unclear",
        ("교환 상태를 알 수 없", "반품 상태를 알 수 없", "환불 상태를 알 수 없"),
    ),
    ("support", "support_unreachable", ("고객센터 연결이 안", "문의 답변이 없")),
    ("notification", "notification_repeated", ("알림이 계속", "알림이 반복")),
    (
        "review_submission",
        "review_submission_failure",
        ("후기 작성이 안", "리뷰 작성이 안", "리뷰 등록이 안"),
    ),
    ("listing_detail", "navigation_lag", ("화면 전환이 버벅", "전환조차 버벅")),
    ("listing", "scroll_position_reset", ("스크롤 위치를 잃", "보던 위치도 못찾", "맨위로 올라")),
    ("cross_cutting_performance", "device_overheating", ("발열",)),
    ("cross_cutting_performance", "app_freeze", ("앱이 먹통", "사이트 먹통", "터치가 안먹")),
)


SYMPTOM_STATEMENTS = {
    "search_result_missing": "검색어와 관련된 결과를 확인할 수 없다고 보고됨",
    "sold_out_mislabel": "상품 상세에서 판매 가능 여부와 품절 표시가 일치하지 않는다고 보고됨",
    "detail_image_missing": "상품 상세 이미지가 표시되지 않거나 깨진다고 보고됨",
    "cart_item_missing": "장바구니에 담은 상품이 유지되지 않는다고 보고됨",
    "checkout_latency": "결제 단계의 응답이 지연된다고 보고됨",
    "external_payment_return_restart": "외부 결제 화면에서 돌아온 뒤 앱 흐름이 다시 시작된다고 보고됨",
    "payment_not_completed": "결제 완료 상태를 확인할 수 없다고 보고됨",
    "promotion_state_mismatch": "미완료 결제와 프로모션 사용 상태가 일치하지 않는다고 보고됨",
    "checkout_blank_screen": "구매 또는 결제 진입 뒤 빈 화면이 표시된다고 보고됨",
    "order_history_missing": "주문 또는 취소 이력을 확인할 수 없다고 보고됨",
    "delivery_delay": "안내된 출고 또는 배송 시점보다 지연된다고 보고됨",
    "exchange_return_status_unclear": "교환·반품·환불 처리 상태를 확인하기 어렵다고 보고됨",
    "support_unreachable": "고객센터 연결 또는 문의 답변을 받기 어렵다고 보고됨",
    "notification_repeated": "동일한 알림이 반복된다고 보고됨",
    "review_submission_failure": "상품 후기 또는 리뷰를 등록할 수 없다고 보고됨",
    "navigation_lag": "목록과 상품 상세 사이 화면 전환이 지연된다고 보고됨",
    "scroll_position_reset": "상품 상세에서 목록으로 돌아온 뒤 기존 스크롤 위치가 유지되지 않는다고 보고됨",
    "device_overheating": "앱 사용 중 기기 발열이 증가한다고 보고됨",
    "app_freeze": "앱 화면 또는 터치 입력이 응답하지 않는다고 보고됨",
    "unclassified_observation": "구체적인 여정 단계와 관찰 증상을 추가로 확인해야 함",
}

TRUSTED_ENVIRONMENT_PROVENANCE = {
    "review_reported",
    "store_metadata",
    "verified_test_run",
}

REPRODUCTION_SPECS = {
    "sold_out_mislabel": {
        "steps": [
            "판매 가능 상태의 대상 상품을 사람이 선정한다",
            "상품 상세에 진입한다",
            "상품 기준 상태·품절 표시·구매 CTA 상태를 함께 기록한다",
        ],
        "oracle_type": "availability_label_cta_consistency",
        "required_observations": [
            "catalog_sellable_state",
            "displayed_availability_label",
            "purchase_cta_state",
        ],
        "human_defined_thresholds": [
            "판매 가능 상태의 판정 기준",
            "품절 표시와 구매 CTA의 기대 정책",
        ],
    },
    "checkout_latency": {
        "steps": [
            "결제 시작 시각과 진입 화면 상태를 기록한다",
            "결제 단계를 진행하며 각 주요 응답 시각을 기록한다",
            "최종 응답 시각·도달 화면·결제 상태를 함께 기록한다",
        ],
        "oracle_type": "checkout_response_timing_and_screen_state",
        "required_observations": [
            "checkout_start_timestamp",
            "checkout_response_timestamps",
            "screen_state_sequence",
            "payment_state",
        ],
        "human_defined_thresholds": [
            "허용 결제 응답 시간",
            "단계별 기대 화면과 결제 상태",
        ],
    },
    "navigation_lag": {
        "steps": [
            "목록→상세→뒤로 이동할 대상 상품과 반복 횟수를 사람이 정한다",
            "목록→상세→뒤로 이동을 반복한다",
            "각 전환의 시작·완료 시각과 화면·스크롤 상태를 기록한다",
        ],
        "oracle_type": "navigation_transition_timing_and_state_continuity",
        "required_observations": [
            "transition_start_timestamp",
            "transition_end_timestamp",
            "rendered_screen_state",
            "list_position_state",
        ],
        "human_defined_thresholds": [
            "허용 화면 전환 시간",
            "뒤로 이동 시 기대 목록·스크롤 상태",
        ],
    },
    "device_overheating": {
        "steps": [
            "동일 환경에서 유휴 기준 상태의 온도·성능을 측정한다",
            "사람이 정한 횟수만큼 목록·상세 탐색을 반복한다",
            "반복 탐색 후 온도·응답 시간·성능 상태를 기준 상태와 비교 기록한다",
        ],
        "oracle_type": "baseline_vs_repeated_navigation_thermal_performance",
        "required_observations": [
            "baseline_temperature",
            "post_navigation_temperature",
            "baseline_response_time",
            "post_navigation_response_time",
        ],
        "human_defined_thresholds": [
            "반복 탐색 횟수와 측정 방법",
            "허용 온도 변화와 성능 저하 기준",
        ],
    },
    "external_payment_return_restart": {
        "steps": [
            "외부 결제 진입 전 주문·결제·프로모션 상태를 기록한다",
            "외부 결제 화면에 진입한 뒤 앱으로 복귀한다",
            "복귀 직후 앱 화면과 주문·결제·프로모션 상태를 비교 기록한다",
        ],
        "oracle_type": "external_payment_return_state_continuity",
        "required_observations": [
            "pre_external_payment_state",
            "return_screen_state",
            "order_state_after_return",
            "payment_state_after_return",
            "promotion_state_after_return",
        ],
        "human_defined_thresholds": [
            "외부 결제 복귀 시 기대 화면",
            "주문·결제·프로모션 상태 보존 정책",
        ],
    },
    "payment_not_completed": {
        "steps": [
            "결제 전 주문·결제 상태를 기록한다",
            "문제가 보고된 결제 흐름을 수행한다",
            "복귀 후 주문·결제 상태와 결제 사업자 응답을 함께 기록한다",
        ],
        "oracle_type": "payment_order_state_consistency",
        "required_observations": [
            "payment_provider_response",
            "order_state",
            "payment_state",
            "displayed_completion_state",
        ],
        "human_defined_thresholds": [
            "결제 성공·실패 판정 기준",
            "주문·결제 상태의 기대 조합",
        ],
    },
    "promotion_state_mismatch": {
        "steps": [
            "결제 전 프로모션 사용 상태를 기록한다",
            "미완료 결제 흐름을 수행한다",
            "결제 미완료 상태와 프로모션 사용 상태를 함께 확인한다",
        ],
        "oracle_type": "payment_promotion_state_consistency",
        "required_observations": [
            "payment_completion_state",
            "promotion_usage_state",
            "promotion_restoration_state",
        ],
        "human_defined_thresholds": [
            "미완료 결제의 판정 기준",
            "실패·취소 시 프로모션 복원 정책",
        ],
    },
}


class InputValidationError(ValueError):
    pass


ALLOWED_SOURCES = {
    "apple_app_store": {"itunes.apple.com", "apps.apple.com"},
    "google_play": {"play.google.com"},
}
MUSINSA_APPLE_APP_ID = "1003139529"
MUSINSA_GOOGLE_PACKAGE = "com.musinsa.store"

HUMAN_DECISIONS = [
    "severity",
    "business_priority",
    "duplicate_confirmation",
    "actual_reproduction_result",
    "policy_violation",
]


def _identifies_musinsa_app(source: str, parsed_url) -> bool:
    if source == "apple_app_store":
        path_segments = {segment for segment in parsed_url.path.split("/") if segment}
        return bool(
            {f"id{MUSINSA_APPLE_APP_ID}", f"id={MUSINSA_APPLE_APP_ID}"}
            & path_segments
        )
    if source == "google_play":
        return parse_qs(parsed_url.query).get("id") == [MUSINSA_GOOGLE_PACKAGE]
    return False


def _validate_payload(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        raise InputValidationError("input must be a JSON object")
    if payload.get("schema_version") != "1.0":
        raise InputValidationError("schema_version must be '1.0'")
    if not isinstance(payload.get("sample_scope"), str) or not payload["sample_scope"].strip():
        raise InputValidationError("sample_scope is required")
    reviews = payload.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        raise InputValidationError("reviews must be a non-empty array")

    required_strings = (
        "evidence_id",
        "source_review_id",
        "source",
        "source_url",
        "review_date",
        "locale",
    )
    seen_evidence_ids: set[str] = set()
    for index, review in enumerate(reviews):
        if not isinstance(review, dict):
            raise InputValidationError(f"reviews[{index}] must be an object")
        for field in required_strings:
            value = review.get(field)
            if not isinstance(value, str) or not value.strip():
                raise InputValidationError(f"reviews[{index}].{field} is required")
        raw_text = review.get("raw_review_text")
        normalized_text = review.get("normalized_observation")
        legacy_text = review.get("text")
        if not any(
            isinstance(value, str) and value.strip()
            for value in (raw_text, normalized_text, legacy_text)
        ):
            raise InputValidationError(
                f"reviews[{index}] requires raw_review_text or normalized_observation"
            )
        if isinstance(raw_text, str) and raw_text.strip():
            actual_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            supplied_hash = review.get("raw_text_sha256")
            if supplied_hash is not None and supplied_hash != actual_hash:
                raise InputValidationError(
                    f"reviews[{index}].raw_text_sha256 does not match raw_review_text"
                )
        is_normalized = isinstance(normalized_text, str) and normalized_text.strip()
        is_legacy_normalized = review.get("text_provenance") == (
            "normalized_observation_from_public_review"
        )
        if is_normalized or is_legacy_normalized:
            if not isinstance(review.get("normalization_method"), str) or not review[
                "normalization_method"
            ].strip():
                raise InputValidationError(
                    f"reviews[{index}].normalization_method is required for normalized text"
                )
            source_hash = review.get("source_raw_text_sha256")
            if not isinstance(source_hash, str) or len(source_hash) != 64:
                raise InputValidationError(
                    f"reviews[{index}].source_raw_text_sha256 is required for normalized text"
                )
        evidence_id = review["evidence_id"]
        if evidence_id in seen_evidence_ids:
            raise InputValidationError(f"reviews[{index}].evidence_id must be unique")
        seen_evidence_ids.add(evidence_id)

        source = review["source"]
        if source not in ALLOWED_SOURCES:
            raise InputValidationError(f"reviews[{index}].source is unsupported")
        parsed_url = urlparse(review["source_url"])
        if parsed_url.scheme != "https" or parsed_url.hostname not in ALLOWED_SOURCES[source]:
            raise InputValidationError(
                f"reviews[{index}].source_url does not match source"
            )
        if not _identifies_musinsa_app(source, parsed_url):
            raise InputValidationError(
                f"reviews[{index}].source_url does not identify the Musinsa app"
            )
        rating = review.get("rating")
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            raise InputValidationError(f"reviews[{index}].rating must be an integer from 1 to 5")
        if "environment" not in review:
            raise InputValidationError(f"reviews[{index}].environment is required")
        if not isinstance(review["environment"], dict):
            raise InputValidationError(f"reviews[{index}].environment must be an object")
    return reviews


def _stable_id(stage: str, symptom: str, evidence_id: str) -> str:
    digest = hashlib.sha256(f"{stage}|{symptom}|{evidence_id}".encode("utf-8")).hexdigest()[:10]
    return f"MUS-{stage.upper()}-{symptom.upper()}-{digest}"


def _review_text_record(review: dict) -> tuple[str, str, dict]:
    raw_text = review.get("raw_review_text")
    legacy_text = review.get("text")
    legacy_is_raw = (
        isinstance(legacy_text, str)
        and legacy_text.strip()
        and review.get("text_provenance")
        != "normalized_observation_from_public_review"
    )
    if isinstance(raw_text, str) and raw_text.strip() or legacy_is_raw:
        raw_text = raw_text if isinstance(raw_text, str) and raw_text.strip() else legacy_text
        raw_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        return raw_text, "raw_review_text", {
            "text_basis": "raw_review_text",
            "raw_review_text": raw_text,
            "raw_text_sha256": raw_hash,
        }

    normalized = review.get("normalized_observation") or review.get("text")
    return normalized, "normalized_observation", {
        "text_basis": "normalized_observation",
        "normalized_observation": normalized,
        "normalization_method": review["normalization_method"],
        "source_raw_text_sha256": review["source_raw_text_sha256"],
        "normalized_text_sha256": hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest(),
    }


def _environment_readiness(environment: dict) -> tuple[str, list[str]]:
    provenance = environment.get("provenance")
    provenance_by_field = provenance if isinstance(provenance, dict) else {}
    information_gaps = []
    synthetic_present = False
    for field in ("device", "os_version", "app_version"):
        if not environment.get(field):
            information_gaps.append(field)
            continue
        field_provenance = (
            provenance_by_field.get(field)
            if isinstance(provenance, dict)
            else (
                "synthetic_test_context"
                if provenance == "synthetic_test_context"
                else None
            )
        )
        if field_provenance == "synthetic_test_context":
            synthetic_present = True
            information_gaps.append(f"{field}_environment_confirmation")
        elif field_provenance not in TRUSTED_ENVIRONMENT_PROVENANCE:
            information_gaps.append(f"{field}_provenance")

    if synthetic_present:
        return "TEST_SCENARIO_ONLY", information_gaps
    if information_gaps:
        return "NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION", information_gaps
    return "READY_FOR_REPRO", information_gaps


def _symptom_spec(symptom: str, stage: str) -> dict:
    return REPRODUCTION_SPECS.get(
        symptom,
        {
            "steps": [
                f"{stage} 여정의 대상 계정·상품·데이터를 사람이 확정한다",
                f"{symptom} 관찰에 대응하는 사용자 동작과 화면 상태를 기록한다",
                "사람이 입력한 기대 정책과 실제 상태를 비교한다",
            ],
            "oracle_type": f"{symptom}_human_defined_acceptance",
            "required_observations": [
                "pre_action_state",
                "user_action_sequence",
                "post_action_state",
            ],
            "human_defined_thresholds": [
                "대상 여정의 기대 정책",
                "허용 상태·시간·횟수 기준",
            ],
        },
    )


def _regression_test(ticket: dict) -> dict:
    symptom = ticket["observed_symptom"]["code"]
    spec = _symptom_spec(symptom, ticket["journey_stage"])
    return {
        "test_id": ticket["ticket_id"].replace("MUS-", "RT-", 1),
        "ticket_id": ticket["ticket_id"],
        "journey_stage": ticket["journey_stage"],
        "symptom_code": ticket["observed_symptom"]["code"],
        "evidence_ids": ticket["evidence_ids"],
        "preconditions": ["테스트 계정·상품·데이터와 환경을 사람이 확정한다"],
        "steps": list(spec["steps"]),
        "oracle_type": spec["oracle_type"],
        "required_observations": list(spec["required_observations"]),
        "human_defined_thresholds": list(spec["human_defined_thresholds"]),
        "automation_candidate": None,
        "automation_assessment": "HUMAN_ASSESSMENT_REQUIRED",
        "human_review_required": True,
    }


def build_report(payload: dict) -> dict:
    reviews = _validate_payload(payload)
    tickets = []
    for review in reviews:
        text, text_basis, review_text_record = _review_text_record(review)
        source_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        environment = review.get("environment") or {}
        status, information_gaps = _environment_readiness(environment)
        review_ticket_count = len(tickets)
        for stage, symptom, phrases in SYMPTOM_RULES:
            phrase_matches = [
                (text.find(phrase), phrase)
                for phrase in phrases
                if text.find(phrase) >= 0
            ]
            if phrase_matches:
                match_start, matched_text = min(phrase_matches, key=lambda item: item[0])
                match_end = match_start + len(matched_text)
                spec = _symptom_spec(symptom, stage)
                tickets.append(
                    {
                        "ticket_id": _stable_id(stage, symptom, review["evidence_id"]),
                        "journey_stage": stage,
                        "observed_symptom": {
                            "code": symptom,
                            "statement": SYMPTOM_STATEMENTS[symptom],
                        },
                        "evidence_ids": [review["evidence_id"]],
                        "source_review_ids": [review["source_review_id"]],
                        "evidence_refs": [
                            {
                                "evidence_id": review["evidence_id"],
                                "source_review_id": review["source_review_id"],
                                "source": review["source"],
                                "source_url": review["source_url"],
                                "review_date": review["review_date"],
                                "rating": review["rating"],
                                "review_text": dict(review_text_record),
                            }
                        ],
                        "matched_evidence": {
                            "text": text[match_start:match_end],
                            "start_offset": match_start,
                            "end_offset": match_end,
                            "source_text_sha256": source_text_sha256,
                            "text_basis": text_basis,
                            "is_raw_review_text": text_basis == "raw_review_text",
                            **(
                                {"raw_text_sha256": source_text_sha256}
                                if text_basis == "raw_review_text"
                                else {
                                    "normalized_text_sha256": source_text_sha256,
                                    "source_raw_text_sha256": review[
                                        "source_raw_text_sha256"
                                    ],
                                }
                            ),
                            "evidence_id": review["evidence_id"],
                            "source_review_id": review["source_review_id"],
                        },
                        "status": status,
                        "information_gaps": information_gaps,
                        "environment": dict(environment),
                        "reproduction_draft": {
                            "preconditions": [
                                "테스트 계정·상품·데이터를 사람이 확정한다"
                            ],
                            "steps": list(spec["steps"]),
                            "expected": "사람이 입력한 정책·임계값과 실제 관찰을 비교한다",
                            "observed": SYMPTOM_STATEMENTS[symptom],
                            "human_validation_required": True,
                        },
                        "human_decisions": list(HUMAN_DECISIONS),
                        "cause_handling": "NOT_GENERATED_FROM_REVIEW",
                    }
                )
        if len(tickets) == review_ticket_count:
            match_start = 0
            match_end = len(text)
            spec = _symptom_spec("unclassified_observation", "unknown")
            tickets.append(
                {
                    "ticket_id": _stable_id(
                        "unknown", "unclassified_observation", review["evidence_id"]
                    ),
                    "journey_stage": "unknown",
                    "observed_symptom": {
                        "code": "unclassified_observation",
                        "statement": SYMPTOM_STATEMENTS["unclassified_observation"],
                    },
                    "evidence_ids": [review["evidence_id"]],
                    "source_review_ids": [review["source_review_id"]],
                    "evidence_refs": [
                        {
                            "evidence_id": review["evidence_id"],
                            "source_review_id": review["source_review_id"],
                            "source": review["source"],
                            "source_url": review["source_url"],
                            "review_date": review["review_date"],
                            "rating": review["rating"],
                            "review_text": dict(review_text_record),
                        }
                    ],
                    "matched_evidence": {
                        "text": text,
                        "start_offset": match_start,
                        "end_offset": match_end,
                        "source_text_sha256": source_text_sha256,
                        "text_basis": text_basis,
                        "is_raw_review_text": text_basis == "raw_review_text",
                        **(
                            {"raw_text_sha256": source_text_sha256}
                            if text_basis == "raw_review_text"
                            else {
                                "normalized_text_sha256": source_text_sha256,
                                "source_raw_text_sha256": review[
                                    "source_raw_text_sha256"
                                ],
                            }
                        ),
                        "evidence_id": review["evidence_id"],
                        "source_review_id": review["source_review_id"],
                    },
                    "status": "NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION",
                    "information_gaps": [*information_gaps, "observable_symptom"],
                    "environment": dict(environment),
                    "reproduction_draft": {
                        "preconditions": ["관찰 증상과 여정 단계를 사람이 명확히 한다"],
                        "steps": list(spec["steps"]),
                        "expected": "관찰 가능한 단일 증상과 사람이 정한 기대값으로 정리된다",
                        "observed": SYMPTOM_STATEMENTS["unclassified_observation"],
                        "human_validation_required": True,
                    },
                    "human_decisions": list(HUMAN_DECISIONS),
                    "cause_handling": "NOT_GENERATED_FROM_REVIEW",
                }
            )
    tickets.sort(key=lambda item: item["ticket_id"])
    regression_tests = [_regression_test(ticket) for ticket in tickets]
    evidence_traceability = {}
    for review in sorted(reviews, key=lambda item: item["evidence_id"]):
        evidence_id = review["evidence_id"]
        evidence_traceability[evidence_id] = {
            "source_review_id": review["source_review_id"],
            "ticket_ids": sorted(
                ticket["ticket_id"]
                for ticket in tickets
                if evidence_id in ticket["evidence_ids"]
            ),
            "regression_test_ids": sorted(
                test["test_id"]
                for test in regression_tests
                if evidence_id in test["evidence_ids"]
            ),
        }
    stable_fields = {
        "tickets": tickets,
        "regression_tests": regression_tests,
        "evidence_traceability": evidence_traceability,
    }
    stable_fields_sha256 = hashlib.sha256(
        json.dumps(
            stable_fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    input_evidence_ids = sorted(review["evidence_id"] for review in reviews)
    derived_evidence_ids = {
        evidence_id for ticket in tickets for evidence_id in ticket["evidence_ids"]
    }
    known_statuses = (
        "READY_FOR_REPRO",
        "TEST_SCENARIO_ONLY",
        "NEEDS_REPRO_AND_ENVIRONMENT_CONFIRMATION",
    )
    status_counts = {
        status: sum(ticket["status"] == status for ticket in tickets)
        for status in known_statuses
    }
    return {
        "schema_version": "1.0",
        "sample_scope": payload.get("sample_scope"),
        "input_evidence_ids": input_evidence_ids,
        "tickets": tickets,
        "regression_tests": regression_tests,
        "evidence_traceability": evidence_traceability,
        "stable_fields_sha256": stable_fields_sha256,
        "summary": {
            "input_reviews": len(reviews),
            "input_evidence_ids": len(input_evidence_ids),
            "tickets": len(tickets),
            "regression_tests": len(regression_tests),
            "status_counts": status_counts,
            "evidence_preservation_rate": (
                len(set(input_evidence_ids) & derived_evidence_ids)
                / len(set(input_evidence_ids))
                if input_evidence_ids
                else 1.0
            ),
        },
        "safety_limits": [
            "공개 리뷰는 사용자 보고이며 실제 장애 또는 전체 사용자 발생률의 증거가 아님",
            "리뷰에서 원인을 생성하지 않음",
            "심각도·우선순위·중복·실제 재현 성공은 사람이 판단함",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="Convert public Musinsa app-review symptoms into evidence-linked QA tickets."
    )
    parser.add_argument("input", type=Path, help="UTF-8 JSON review fixture")
    parser.add_argument("--output", "-o", type=Path, help="Write report JSON to this path")
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        report = build_report(payload)
    except (OSError, json.JSONDecodeError, InputValidationError, KeyError, TypeError) as exc:
        print(
            json.dumps(
                {"error": "INVALID_INPUT", "message": str(exc)}, ensure_ascii=False
            ),
            file=sys.stderr,
        )
        return 2

    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
