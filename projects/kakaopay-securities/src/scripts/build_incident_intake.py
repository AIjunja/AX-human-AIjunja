from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
from collections import Counter
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, unquote, urlparse


SCHEMA_VERSION = "1.0.0"
CASE_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{2,79}$")
EVIDENCE_ID_RE = re.compile(r"^[A-Z0-9][A-Z0-9._:-]{2,127}$")

TOP_LEVEL_FIELDS = {
    "schema_version",
    "case_id",
    "observed_window",
    "public_reports",
    "official_sources",
}
WINDOW_FIELDS = {"start", "end"}
COMMON_SOURCE_FIELDS = {
    "evidence_id",
    "source_record_id",
    "source_url",
    "source_type",
    "published_at",
    "captured_at",
    "text",
}
PUBLIC_REPORT_FIELDS = COMMON_SOURCE_FIELDS | {
    "rating",
    "platform",
    "app_version",
    "is_edited",
    "device_os",
    "network",
    "exact_occurred_at",
    "reproduction_steps",
    "expected_result",
    "actual_result",
}
OFFICIAL_SOURCE_FIELDS = COMMON_SOURCE_FIELDS
PUBLIC_SOURCE_TYPES = {
    "google_play_review",
    "apple_app_store_review",
    "other_public_report",
}
OFFICIAL_SOURCE_TYPES = {
    "kps_official_notice",
    "public_standard",
    "public_market_notice",
}
PLATFORM_VALUES = {"android", "ios", "web", "other"}

TRUSTED_PUBLIC_STANDARD_HOSTS = {
    "law.kofia.or.kr",
    "law.go.kr",
    "www.law.go.kr",
    "fsc.go.kr",
    "www.fsc.go.kr",
    "fss.or.kr",
    "www.fss.or.kr",
}
TRUSTED_PUBLIC_MARKET_HOSTS = {
    "krx.co.kr",
    "www.krx.co.kr",
    "global.krx.co.kr",
    "kind.krx.co.kr",
    "data.krx.co.kr",
}

SENSITIVE_FIELD_NAMES = {
    "account_number",
    "customer_name",
    "email",
    "order_number",
    "phone",
    "resident_registration_number",
}
SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b\d{6}-[1-4]\d{6}\b"),
    re.compile(r"(?<!\d)01[016789][ -]?\d{3,4}[ -]?\d{4}(?!\d)"),
    re.compile(
        r"(?:계좌(?:번호)?|주문(?:번호)?|account\s*(?:number|no\.?|id)|"
        r"order\s*(?:number|no\.?|id))\s*[:#]?\s*[0-9][0-9 -]{5,}",
        re.IGNORECASE,
    ),
)

SIGNAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "SECURITIES_SURFACE",
        re.compile(r"증권|주식\s*(?:탭|홈|화면)|securities|stock", re.IGNORECASE),
    ),
    (
        "ORDER_CONTROL",
        re.compile(r"매수|매도|구매|판매|주문|buy|sell|order", re.IGNORECASE),
    ),
    (
        "MARKET_DATA",
        re.compile(r"시세|관심|커뮤니티|호가|market\s*data|quote", re.IGNORECASE),
    ),
    (
        "ACCOUNT_FUNDS",
        re.compile(r"예수금|주문가능|잔고|계좌|balance|funds", re.IGNORECASE),
    ),
    (
        "UNAVAILABLE",
        re.compile(
            r"먹통|접속\s*안|접속안|안\s*열|열리지|못합니다|불가|"
            r"오류|unavailable|cannot|can't|not\s+open",
            re.IGNORECASE,
        ),
    ),
    (
        "LOADING_STUCK",
        re.compile(r"로딩\s*(?:중|만)|멈춤|stuck|loading", re.IGNORECASE),
    ),
    (
        "FORCED_EXIT",
        re.compile(r"강제\s*종료|튕|꺼지|crash|forced\s*exit", re.IGNORECASE),
    ),
    (
        "DISPLAY_ERROR",
        re.compile(r"사라|잘려|중복|확대|표시|display|cropp|disappear", re.IGNORECASE),
    ),
)

MISSING_REPRO_FIELDS = (
    "platform",
    "app_version",
    "device_os",
    "network",
    "exact_occurred_at",
    "reproduction_steps",
    "expected_result",
    "actual_result",
)

PROHIBITED_CONCLUSIONS = (
    "INVESTMENT_RECOMMENDATION",
    "TRADE_EXECUTION",
    "LOSS_CALCULATION",
    "COMPENSATION_ELIGIBILITY",
    "COMPANY_FAULT",
    "ROOT_CAUSE",
)
FORBIDDEN_OUTPUT_KEYS = (
    "recommended_trade",
    "trade_instruction",
    "loss_amount",
    "compensation_decision",
    "liability_decision",
    "root_cause",
)


class InputValidationError(ValueError):
    """Raised when public incident input cannot be processed safely."""

    def __init__(self, errors: list[dict[str, str]]) -> None:
        self.errors = errors
        super().__init__("; ".join(error["code"] for error in errors))

    @property
    def codes(self) -> list[str]:
        return [error["code"] for error in self.errors]


def _add_error(
    errors: list[dict[str, str]], code: str, path: str, message: str
) -> None:
    errors.append({"code": code, "path": path, "message": message})


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _parse_iso(value: object) -> date | datetime | None:
    if not _non_empty_string(value):
        return None
    raw = str(value)
    try:
        if "T" in raw or " " in raw:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _parse_aware_datetime(value: object) -> datetime | None:
    parsed = _parse_iso(value)
    if not isinstance(parsed, datetime):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _https_url(value: object) -> bool:
    if not _non_empty_string(value):
        return False
    parsed = urlparse(str(value))
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    if hostname == "localhost" or hostname.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return "." in hostname
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_unspecified
    )


def _trusted_source_url(row: dict[str, Any]) -> bool:
    raw_url = row.get("source_url")
    source_type = row.get("source_type")
    source_record_id = str(row.get("source_record_id", ""))
    if not _https_url(raw_url) or not isinstance(source_type, str):
        return False
    parsed = urlparse(str(raw_url))
    host = (parsed.hostname or "").lower().rstrip(".")
    path = parsed.path.rstrip("/")
    query = parse_qs(parsed.query)

    if source_type == "google_play_review":
        return (
            host == "play.google.com"
            and path == "/store/apps/details"
            and query.get("id") == ["com.kakaopay.app"]
            and query.get("reviewId") == [source_record_id]
        )
    if source_type == "apple_app_store_review":
        return host == "apps.apple.com" and path.endswith("/id1464496236")
    if source_type == "kps_official_notice":
        return (
            host in {"kakaopaysec.com", "www.kakaopaysec.com"}
            and path
            in {
                "/customer/notice/dynamicBoardPageDetail.do",
                "/stocknotice/instocknotice/dynamicBoardPageDetail.do",
            }
            and query.get("id") == [source_record_id]
            and source_record_id.isdigit()
        )
    if source_type == "public_standard":
        return host in TRUSTED_PUBLIC_STANDARD_HOSTS
    if source_type == "public_market_notice":
        return host in TRUSTED_PUBLIC_MARKET_HOSTS
    if source_type == "other_public_report":
        return True
    return False


def _canonical_url_key(value: str) -> tuple[str, str, tuple[tuple[str, tuple[str, ...]], ...]]:
    parsed = urlparse(value)
    return (
        (parsed.hostname or "").lower().rstrip("."),
        parsed.path.rstrip("/"),
        tuple(
            (key, tuple(sorted(values)))
            for key, values in sorted(parse_qs(parsed.query).items())
        ),
    )


def _normalized_content_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _sensitive_paths(value: object, path: str = "$") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).lower() in SENSITIVE_FIELD_NAMES:
                yield child_path
            yield from _sensitive_paths(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _sensitive_paths(child, f"{path}[{index}]")


def _string_values(value: object, path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from _string_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _string_values(child, f"{path}[{index}]")


def _has_sensitive_text(value: str) -> bool:
    decoded = unquote(value)
    return any(
        pattern.search(candidate)
        for pattern in SENSITIVE_TEXT_PATTERNS
        for candidate in (value, decoded)
    )


def _validate_source_record(
    row: object,
    path: str,
    *,
    allowed_fields: set[str],
    allowed_types: set[str],
    public_report: bool,
    errors: list[dict[str, str]],
) -> None:
    if not isinstance(row, dict):
        _add_error(errors, "SOURCE_NOT_OBJECT", path, "Source record must be an object.")
        return

    for field in sorted(set(row) - allowed_fields):
        if field in SENSITIVE_FIELD_NAMES:
            _add_error(
                errors,
                "SENSITIVE_FIELD_FORBIDDEN",
                f"{path}.{field}",
                "Personal, account, or order identifiers are not accepted.",
            )
        else:
            _add_error(
                errors,
                "UNKNOWN_FIELD",
                f"{path}.{field}",
                "Unsupported input field.",
            )

    for field in sorted(COMMON_SOURCE_FIELDS):
        if field not in row:
            _add_error(
                errors,
                "REQUIRED_FIELD_MISSING",
                f"{path}.{field}",
                "Required source field is missing.",
            )

    evidence_id = row.get("evidence_id")
    if not _non_empty_string(evidence_id) or EVIDENCE_ID_RE.fullmatch(str(evidence_id)) is None:
        _add_error(
            errors,
            "EVIDENCE_ID_INVALID",
            f"{path}.evidence_id",
            "Evidence ID must be an uppercase stable identifier.",
        )
    if not _non_empty_string(row.get("source_record_id")):
        _add_error(
            errors,
            "SOURCE_RECORD_ID_INVALID",
            f"{path}.source_record_id",
            "Source record ID must be non-empty.",
        )
    if not _https_url(row.get("source_url")):
        _add_error(
            errors,
            "SOURCE_URL_NOT_HTTPS",
            f"{path}.source_url",
            "Source URL must be a public HTTPS URL.",
        )
    source_type = row.get("source_type")
    if source_type not in allowed_types:
        _add_error(
            errors,
            "SOURCE_TYPE_INVALID",
            f"{path}.source_type",
            "Source type is not accepted for this collection.",
        )
    elif _https_url(row.get("source_url")) and not _trusted_source_url(row):
        _add_error(
            errors,
            "UNTRUSTED_SOURCE_URL",
            f"{path}.source_url",
            "Source URL does not match the declared public source type and record ID.",
        )

    published_at = _parse_iso(row.get("published_at"))
    if published_at is None or (
        isinstance(published_at, datetime)
        and (published_at.tzinfo is None or published_at.utcoffset() is None)
    ):
        _add_error(
            errors,
            "SOURCE_DATE_INVALID",
            f"{path}.published_at",
            "published_at must be an ISO date or timezone-aware datetime.",
        )
    if _parse_aware_datetime(row.get("captured_at")) is None:
        _add_error(
            errors,
            "SOURCE_DATE_INVALID",
            f"{path}.captured_at",
            "captured_at must be a timezone-aware ISO datetime.",
        )
    if not _non_empty_string(row.get("text")):
        _add_error(
            errors,
            "SOURCE_TEXT_EMPTY",
            f"{path}.text",
            "Source text must be non-empty.",
        )

    for string_path, string_value in _string_values(row, path):
        if _has_sensitive_text(string_value):
            _add_error(
                errors,
                "SENSITIVE_TEXT_DETECTED",
                string_path,
                "Accepted input strings must not contain high-confidence personal, account, or order identifiers.",
            )

    if public_report:
        rating = row.get("rating")
        if rating is not None and (
            not isinstance(rating, int)
            or isinstance(rating, bool)
            or not 1 <= rating <= 5
        ):
            _add_error(
                errors,
                "RATING_INVALID",
                f"{path}.rating",
                "Rating must be an integer from 1 to 5.",
            )
        if "is_edited" in row and not isinstance(row.get("is_edited"), bool):
            _add_error(
                errors,
                "EDITED_FLAG_INVALID",
                f"{path}.is_edited",
                "is_edited must be boolean when present.",
            )
        if "platform" in row and (
            not isinstance(row.get("platform"), str)
            or row.get("platform") not in PLATFORM_VALUES
        ):
            _add_error(
                errors,
                "PLATFORM_INVALID",
                f"{path}.platform",
                f"platform must be one of: {', '.join(sorted(PLATFORM_VALUES))}.",
            )
        for field in (
            "app_version",
            "device_os",
            "network",
            "expected_result",
            "actual_result",
        ):
            if field in row and not _non_empty_string(row.get(field)):
                _add_error(
                    errors,
                    "OPTIONAL_TEXT_INVALID",
                    f"{path}.{field}",
                    "Optional reproduction fields must be non-empty strings when present.",
                )
        if "exact_occurred_at" in row and _parse_aware_datetime(
            row.get("exact_occurred_at")
        ) is None:
            _add_error(
                errors,
                "EXACT_OCCURRED_AT_INVALID",
                f"{path}.exact_occurred_at",
                "exact_occurred_at must be a timezone-aware ISO datetime.",
            )
        if "reproduction_steps" in row and not (
            isinstance(row.get("reproduction_steps"), list)
            and bool(row["reproduction_steps"])
            and all(_non_empty_string(item) for item in row["reproduction_steps"])
        ):
            _add_error(
                errors,
                "REPRODUCTION_STEPS_INVALID",
                f"{path}.reproduction_steps",
                "Reproduction steps must be a non-empty string array.",
            )


def validate_input(payload: object) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    if not isinstance(payload, dict):
        raise InputValidationError(
            [
                {
                    "code": "INPUT_NOT_OBJECT",
                    "path": "$",
                    "message": "Input JSON must be an object.",
                }
            ]
        )

    for path in sorted(set(_sensitive_paths(payload))):
        _add_error(
            errors,
            "SENSITIVE_FIELD_FORBIDDEN",
            path,
            "Personal, account, or order identifiers are not accepted.",
        )

    for field in sorted(set(payload) - TOP_LEVEL_FIELDS):
        _add_error(errors, "UNKNOWN_FIELD", f"$.{field}", "Unsupported top-level field.")
    for field in sorted(TOP_LEVEL_FIELDS):
        if field not in payload:
            _add_error(
                errors,
                "REQUIRED_FIELD_MISSING",
                f"$.{field}",
                "Required top-level field is missing.",
            )

    if payload.get("schema_version") != SCHEMA_VERSION:
        _add_error(
            errors,
            "SCHEMA_VERSION_UNSUPPORTED",
            "$.schema_version",
            f"schema_version must be {SCHEMA_VERSION}.",
        )
    case_id = payload.get("case_id")
    if not _non_empty_string(case_id) or CASE_ID_RE.fullmatch(str(case_id)) is None:
        _add_error(
            errors,
            "CASE_ID_INVALID",
            "$.case_id",
            "case_id must be an uppercase hyphen-delimited identifier.",
        )

    observed_window = payload.get("observed_window")
    start: datetime | None = None
    end: datetime | None = None
    if not isinstance(observed_window, dict):
        _add_error(
            errors,
            "OBSERVED_WINDOW_INVALID",
            "$.observed_window",
            "observed_window must be an object.",
        )
    else:
        for field in sorted(set(observed_window) - WINDOW_FIELDS):
            _add_error(
                errors,
                "UNKNOWN_FIELD",
                f"$.observed_window.{field}",
                "Unsupported observed window field.",
            )
        start = _parse_aware_datetime(observed_window.get("start"))
        end = _parse_aware_datetime(observed_window.get("end"))
        if start is None:
            _add_error(
                errors,
                "OBSERVED_WINDOW_INVALID",
                "$.observed_window.start",
                "Window start must be a timezone-aware ISO datetime.",
            )
        if end is None:
            _add_error(
                errors,
                "OBSERVED_WINDOW_INVALID",
                "$.observed_window.end",
                "Window end must be a timezone-aware ISO datetime.",
            )
        if start is not None and end is not None and start > end:
            _add_error(
                errors,
                "OBSERVED_WINDOW_REVERSED",
                "$.observed_window",
                "Window start must not be after window end.",
            )

    public_reports = payload.get("public_reports")
    official_sources = payload.get("official_sources")
    if not isinstance(public_reports, list) or not public_reports:
        _add_error(
            errors,
            "PUBLIC_REPORTS_EMPTY",
            "$.public_reports",
            "At least one public report is required.",
        )
        public_reports = []
    if not isinstance(official_sources, list):
        _add_error(
            errors,
            "OFFICIAL_SOURCES_INVALID",
            "$.official_sources",
            "official_sources must be an array.",
        )
        official_sources = []

    for index, row in enumerate(public_reports):
        _validate_source_record(
            row,
            f"$.public_reports[{index}]",
            allowed_fields=PUBLIC_REPORT_FIELDS,
            allowed_types=PUBLIC_SOURCE_TYPES,
            public_report=True,
            errors=errors,
        )
    for index, row in enumerate(official_sources):
        _validate_source_record(
            row,
            f"$.official_sources[{index}]",
            allowed_fields=OFFICIAL_SOURCE_FIELDS,
            allowed_types=OFFICIAL_SOURCE_TYPES,
            public_report=False,
            errors=errors,
        )

    evidence_ids: list[str] = []
    source_keys: list[tuple[str, str]] = []
    source_url_keys: list[
        tuple[str, str, tuple[tuple[str, tuple[str, ...]], ...]]
    ] = []
    public_content_keys: list[str] = []
    for row in [*public_reports, *official_sources]:
        if isinstance(row, dict):
            if _non_empty_string(row.get("evidence_id")):
                evidence_ids.append(str(row["evidence_id"]))
            if _non_empty_string(row.get("source_type")) and _non_empty_string(
                row.get("source_record_id")
            ):
                source_keys.append(
                    (str(row["source_type"]), str(row["source_record_id"]))
                )
            if (
                _https_url(row.get("source_url"))
                and row.get("source_type") != "apple_app_store_review"
            ):
                source_url_keys.append(_canonical_url_key(str(row["source_url"])))
    for row in public_reports:
        if isinstance(row, dict) and _non_empty_string(row.get("text")):
            public_content_keys.append(_normalized_content_key(str(row["text"])))
    for evidence_id, count in sorted(Counter(evidence_ids).items()):
        if count > 1:
            _add_error(
                errors,
                "DUPLICATE_EVIDENCE_ID",
                "$",
                f"Evidence ID is duplicated: {evidence_id}",
            )
    for source_key, count in sorted(Counter(source_keys).items()):
        if count > 1:
            _add_error(
                errors,
                "DUPLICATE_SOURCE_RECORD",
                "$",
                f"Source record is duplicated: {source_key[0]}:{source_key[1]}",
            )
    for source_url_key, count in sorted(Counter(source_url_keys).items()):
        if count > 1:
            _add_error(
                errors,
                "DUPLICATE_SOURCE_URL",
                "$",
                f"Source URL is duplicated: {source_url_key[0]}{source_url_key[1]}",
            )
    for content_key, count in sorted(Counter(public_content_keys).items()):
        if count > 1:
            _add_error(
                errors,
                "DUPLICATE_SOURCE_CONTENT",
                "$.public_reports",
                "Exact normalized public-report content must not fill multiple evidence slots.",
            )

    if errors:
        unique: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for error in errors:
            signature = (error["code"], error["path"], error["message"])
            if signature not in seen:
                seen.add(signature)
                unique.append(error)
        raise InputValidationError(unique)
    return payload


def _content_sha256(text_value: str) -> str:
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()


def _canonical_input_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sort_instant(raw: str, reference_timezone: Any) -> datetime:
    parsed = _parse_iso(raw)
    if isinstance(parsed, datetime):
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=reference_timezone)
        return parsed.astimezone(reference_timezone)
    assert isinstance(parsed, date)
    return datetime.combine(parsed, time.min, tzinfo=reference_timezone)


def _in_window(raw: str, start: datetime, end: datetime) -> bool:
    parsed = _parse_iso(raw)
    if isinstance(parsed, datetime):
        if parsed.tzinfo is None:
            return False
        normalized = parsed.astimezone(start.tzinfo)
        return start <= normalized <= end
    return False


def _reported_signal_codes(row: dict[str, Any]) -> set[str]:
    return {
        code
        for code, pattern in SIGNAL_PATTERNS
        if pattern.search(str(row.get("text", "")))
    }


def _report_time_bucket(
    row: dict[str, Any], start: datetime, end: datetime
) -> str:
    exact_occurred_at = row.get("exact_occurred_at")
    if exact_occurred_at is not None:
        return "EXACT_IN_WINDOW" if _in_window(exact_occurred_at, start, end) else "OUTSIDE_WINDOW"
    published_at = _parse_iso(row["published_at"])
    if isinstance(published_at, datetime):
        return "EXACT_IN_WINDOW" if _in_window(row["published_at"], start, end) else "OUTSIDE_WINDOW"
    if isinstance(published_at, date) and start.date() <= published_at <= end.date():
        return "UNRESOLVED_DATE_ONLY_SAME_DAY"
    return "OUTSIDE_WINDOW"


def _build_temporal_association(
    public_reports: list[dict[str, Any]],
    official_sources: list[dict[str, Any]],
    start: datetime,
    end: datetime,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    exact_window_report_ids: list[str] = []
    unresolved_report_ids: list[str] = []
    outside_window_report_ids: list[str] = []
    topic_irrelevant_report_ids: list[str] = []
    candidate_reports: list[dict[str, Any]] = []
    disruption_codes = {"UNAVAILABLE", "LOADING_STUCK", "FORCED_EXIT", "DISPLAY_ERROR"}

    for row in public_reports:
        bucket = _report_time_bucket(row, start, end)
        if bucket == "EXACT_IN_WINDOW":
            exact_window_report_ids.append(row["evidence_id"])
        elif bucket == "UNRESOLVED_DATE_ONLY_SAME_DAY":
            unresolved_report_ids.append(row["evidence_id"])
        else:
            outside_window_report_ids.append(row["evidence_id"])

        codes = _reported_signal_codes(row)
        topic_relevant = "SECURITIES_SURFACE" in codes and bool(codes & disruption_codes)
        if not topic_relevant:
            topic_irrelevant_report_ids.append(row["evidence_id"])
        if topic_relevant and bucket in {
            "EXACT_IN_WINDOW",
            "UNRESOLVED_DATE_ONLY_SAME_DAY",
        }:
            candidate_reports.append(row)

    official_in_window: list[dict[str, Any]] = []
    date_only_official_source_ids: list[str] = []
    outside_window_official_source_ids: list[str] = []
    for row in official_sources:
        if row["source_type"] != "kps_official_notice":
            continue
        parsed = _parse_iso(row["published_at"])
        if isinstance(parsed, date) and not isinstance(parsed, datetime):
            date_only_official_source_ids.append(row["evidence_id"])
        elif _in_window(row["published_at"], start, end):
            official_in_window.append(row)
        else:
            outside_window_official_source_ids.append(row["evidence_id"])

    association = {
        "rule": "SECURITIES_DISRUPTION_SIGNAL_AND_EXACT_WINDOW_OR_UNRESOLVED_SAME_DAY",
        "candidate_report_count": len(candidate_reports),
        "candidate_report_ids": sorted(row["evidence_id"] for row in candidate_reports),
        "exact_window_report_ids": sorted(exact_window_report_ids),
        "unresolved_report_ids": sorted(unresolved_report_ids),
        "outside_window_report_ids": sorted(outside_window_report_ids),
        "topic_irrelevant_report_ids": sorted(topic_irrelevant_report_ids),
        "exact_window_official_source_ids": sorted(
            row["evidence_id"] for row in official_in_window
        ),
        "date_only_official_source_ids": sorted(date_only_official_source_ids),
        "outside_window_official_source_ids": sorted(
            outside_window_official_source_ids
        ),
    }
    return association, candidate_reports, official_in_window


def _extract_reported_signals(public_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for code, pattern in SIGNAL_PATTERNS:
        evidence_ids = sorted(
            row["evidence_id"] for row in public_reports if pattern.search(row["text"])
        )
        if evidence_ids:
            signals.append(
                {
                    "code": code,
                    "fact_status": "PUBLICLY_REPORTED",
                    "evidence_ids": evidence_ids,
                }
            )
    return signals


def _missing_information(public_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in public_reports:
        missing = []
        for field in MISSING_REPRO_FIELDS:
            value = row.get(field)
            if value is None or value == "" or value == []:
                missing.append(field)
        if missing:
            output.append(
                {
                    "evidence_id": row["evidence_id"],
                    "fields": missing,
                }
            )
    return sorted(output, key=lambda item: item["evidence_id"])


def _source_conflicts(
    public_reports: list[dict[str, Any]],
    official_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    order_unavailable_ids = sorted(
        row["evidence_id"]
        for row in public_reports
        if re.search(r"매수|매도|구매|판매|주문|buy|sell|order", row["text"], re.IGNORECASE)
        and re.search(
            r"먹통|접속\s*안|안\s*열|열리지|못합니다|불가|오류|cannot|unavailable",
            row["text"],
            re.IGNORECASE,
        )
    )
    official_normal_ids = sorted(
        row["evidence_id"]
        for row in official_sources
        if re.search(
            r"주식\s*주문(?:은|이)?\s*정상|orders?\s+(?:are\s+)?normal",
            row["text"],
            re.IGNORECASE,
        )
    )
    if order_unavailable_ids and official_normal_ids:
        return [
            {
                "code": "ORDER_STATUS_DIVERGENCE",
                "resolution": "HUMAN_REVIEW_REQUIRED",
                "evidence_ids": [*order_unavailable_ids, *official_normal_ids],
            }
        ]
    return []


def _nested_keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(str(key))
            found.update(_nested_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_nested_keys(child))
    return found


def build_packet(payload: object) -> dict[str, Any]:
    validated = validate_input(payload)
    public_reports: list[dict[str, Any]] = validated["public_reports"]
    official_sources: list[dict[str, Any]] = validated["official_sources"]
    start = _parse_aware_datetime(validated["observed_window"]["start"])
    end = _parse_aware_datetime(validated["observed_window"]["end"])
    assert start is not None and end is not None

    rows_with_status = [
        *((row, "PUBLICLY_REPORTED") for row in public_reports),
        *((row, "OFFICIALLY_STATED" if row["source_type"] == "kps_official_notice" else "PUBLIC_STANDARD") for row in official_sources),
    ]
    evidence_registry = sorted(
        [
            {
                "evidence_id": row["evidence_id"],
                "source_record_id": row["source_record_id"],
                "source_url": row["source_url"],
                "source_type": row["source_type"],
                "published_at": row["published_at"],
                "captured_at": row["captured_at"],
                "content_sha256": _content_sha256(row["text"]),
                "fact_status": fact_status,
            }
            for row, fact_status in rows_with_status
        ],
        key=lambda item: item["evidence_id"],
    )

    timeline = sorted(
        [
            {
                "published_at": row["published_at"],
                "source_type": row["source_type"],
                "fact_status": fact_status,
                "evidence_ids": [row["evidence_id"]],
            }
            for row, fact_status in rows_with_status
        ],
        key=lambda item: (
            _sort_instant(item["published_at"], start.tzinfo),
            item["evidence_ids"][0],
        ),
    )
    reported_signals = _extract_reported_signals(public_reports)
    missing_information = _missing_information(public_reports)
    (
        temporal_association,
        candidate_reports,
        official_in_window_rows,
    ) = _build_temporal_association(
        public_reports,
        official_sources,
        start,
        end,
    )
    conflicts = _source_conflicts(candidate_reports, official_in_window_rows)
    official_in_window = sorted(
        row["evidence_id"] for row in official_in_window_rows
    )
    official_status = (
        "OFFICIAL_SOURCE_IN_WINDOW"
        if official_in_window
        else "NO_MATCHING_OFFICIAL_SOURCE"
    )
    workflow_status = (
        "READY_FOR_HUMAN_TRIAGE"
        if len(candidate_reports) >= 2 and bool(official_in_window)
        else "NEEDS_MORE_PUBLIC_INFORMATION"
    )

    source_type_counts = Counter(
        row["source_type"] for row in [*public_reports, *official_sources]
    )
    prohibited = [
        {"code": code, "status": "NOT_ASSESSED"}
        for code in PROHIBITED_CONCLUSIONS
    ]
    input_ids = {
        row["evidence_id"] for row in [*public_reports, *official_sources]
    }
    registry_ids = {row["evidence_id"] for row in evidence_registry}
    preservation_percent = (
        100
        if input_ids == registry_ids
        else round(len(input_ids & registry_ids) * 100 / max(1, len(input_ids)))
    )
    proof_line = (
        "KPS_PUBLIC_INCIDENT_INTAKE_OK:v1"
        f"|case={validated['case_id']}"
        f"|status={workflow_status}"
        f"|evidence={len(evidence_registry)}"
        f"|reports={len(public_reports)}"
        f"|official={len(official_sources)}"
        f"|preserved={preservation_percent}%"
        "|forbidden=PASS"
    )

    human_review_reasons = {"PUBLIC_REPORTS_ARE_NOT_INTERNAL_INCIDENT_CONFIRMATION"}
    if missing_information:
        human_review_reasons.add("MISSING_REPRODUCTION_CONTEXT")
    if conflicts:
        human_review_reasons.add("SOURCE_DIVERGENCE")
    if set(temporal_association["candidate_report_ids"]) & set(
        temporal_association["unresolved_report_ids"]
    ):
        human_review_reasons.add("UNRESOLVED_TEMPORAL_ASSOCIATION")
    if len(candidate_reports) < 2:
        human_review_reasons.add("INSUFFICIENT_RELEVANT_PUBLIC_REPORTS")

    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "case_id": validated["case_id"],
        "input_sha256": _canonical_input_sha256(validated),
        "workflow_status": workflow_status,
        "event_classification": "PUBLIC_REPORT_CLUSTER",
        "source_coverage": {
            "public_report_count": len(public_reports),
            "candidate_public_report_count": len(candidate_reports),
            "official_source_count": len(official_sources),
            "by_source_type": dict(sorted(source_type_counts.items())),
        },
        "evidence_registry": evidence_registry,
        "timeline": timeline,
        "temporal_association": temporal_association,
        "reported_signals": reported_signals,
        "official_corroboration": {
            "status": official_status,
            "scope": "WINDOW_ONLY_NOT_CAUSE_FAULT_OR_INDIVIDUAL_REPORT_CONFIRMATION",
            "evidence_ids": official_in_window,
        },
        "source_conflicts": conflicts,
        "missing_information": missing_information,
        "human_review": {
            "required": True,
            "reasons": sorted(human_review_reasons),
            "next_actions": [
                "VERIFY_AGAINST_AUTHORIZED_INTERNAL_TELEMETRY",
                "CONFIRM_AFFECTED_SURFACE_AND_TIME_WINDOW",
                "KEEP_FINAL_OPERATIONAL_AND_COMPLIANCE_JUDGMENT_WITH_HUMANS",
            ],
        },
        "prohibited_conclusions": prohibited,
        "safety_review": {
            "result": "PASS",
            "evidence_id_preservation_percent": preservation_percent,
            "unpreserved_evidence_ids": sorted(input_ids - registry_ids),
            "forbidden_output_keys_present": [],
            "personal_data_scan": "PASS",
            "personal_data_scan_scope": "ALL_ACCEPTED_STRING_FIELDS_HIGH_CONFIDENCE_PATTERNS",
        },
        "proof_line": proof_line,
    }

    forbidden_present = sorted(_nested_keys(packet) & set(FORBIDDEN_OUTPUT_KEYS))
    if forbidden_present:
        raise RuntimeError("Forbidden output key generated.")
    return packet


def _error_payload(
    errors: list[dict[str, str]], error: str = "INPUT_VALIDATION_FAILED"
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a source-preserving public incident intake packet."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--proof-only", action="store_true")
    args = parser.parse_args(argv)

    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        packet = build_packet(payload)
    except InputValidationError as exc:
        print(
            json.dumps(
                _error_payload(exc.errors),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                _error_payload(
                    [
                        {
                            "code": "INPUT_FILE_INVALID",
                            "path": str(args.input),
                            "message": type(exc).__name__,
                        }
                    ],
                    error="INPUT_FILE_INVALID",
                ),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2

    if args.proof_only:
        print(packet["proof_line"])
    elif args.compact:
        print(
            json.dumps(
                packet,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    else:
        print(json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
