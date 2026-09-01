from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


POC_THRESHOLDS = {
    "useful_discoveries_min": 50,
    "valid_rate_min": 0.90,
    "stale_rate_max_exclusive": 0.05,
    "duplicate_rate_max_exclusive": 0.05,
    "source_types_min": 5,
    "relevance_rate_min": 0.70,
    "merchant_onboarding_max": 0,
}


@dataclass(frozen=True, slots=True)
class AuditCounts:
    useful_discoveries: int | None = None
    valid_open_sample: int | None = None
    valid_open_count: int | None = None
    relevance_sample: int | None = None
    relevant_count: int | None = None
    merchant_onboarding_count: int | None = None


@dataclass(frozen=True, slots=True)
class DailyMeasurement:
    accepted: bool
    passed: bool
    complete: bool
    gates: Mapping[str, bool | None]
    metrics: Mapping[str, int | float | None]
    reasons: tuple[str, ...]


def evaluate_daily(
    *,
    ingestion_status: str,
    ingestion_metrics: Mapping[str, object],
    source_results: Sequence[Mapping[str, object]],
    audit: AuditCounts,
) -> DailyMeasurement:
    reasons: list[str] = []

    candidate_count = _int_metric(ingestion_metrics, "candidate_count")
    duplicate_count = _int_metric(ingestion_metrics, "duplicate_count")
    expired_count = _int_metric(ingestion_metrics, "expired_count")
    ranked_count = _int_metric(ingestion_metrics, "ranked_count")
    failed_count = _int_metric(ingestion_metrics, "failed_count")

    contributing = [
        item
        for item in source_results
        if item.get("status") == "ok" and int(item.get("candidate_count") or 0) > 0
    ]
    missing_classes = [item for item in contributing if not str(item.get("source_class") or "").strip()]
    if missing_classes:
        reasons.append("source_class evidence is required for every contributing source")
    source_types = len(
        {
            str(item.get("source_class")).strip()
            for item in contributing
            if str(item.get("source_class") or "").strip()
        }
    )

    duplicate_rate = duplicate_count / candidate_count if candidate_count else None
    stale_rate = expired_count / candidate_count if candidate_count else None

    valid_rate = _ratio(
        audit.valid_open_count,
        audit.valid_open_sample,
        "valid-open",
        reasons,
    )
    relevance_rate = _ratio(
        audit.relevant_count,
        audit.relevance_sample,
        "relevance",
        reasons,
    )

    merchant_onboarding_count = audit.merchant_onboarding_count
    if merchant_onboarding_count is None:
        merchant_onboarding_count = _optional_int_metric(
            ingestion_metrics,
            "merchant_onboarding_count",
        )

    if ingestion_status != "completed":
        reasons.append(f"ingestion_status={ingestion_status}")
    if failed_count:
        reasons.append(f"failed_count={failed_count}")
    if candidate_count <= 0:
        reasons.append("candidate_count must be > 0")
    if audit.useful_discoveries is None:
        reasons.append("useful_discoveries audit is required")
    if merchant_onboarding_count is None:
        reasons.append("merchant_onboarding_count evidence is required")

    gates: dict[str, bool | None] = {
        "useful_discoveries": (
            audit.useful_discoveries >= POC_THRESHOLDS["useful_discoveries_min"]
            if audit.useful_discoveries is not None
            else None
        ),
        "valid_when_opened": (
            valid_rate >= POC_THRESHOLDS["valid_rate_min"] if valid_rate is not None else None
        ),
        "stale_expired": (
            stale_rate < POC_THRESHOLDS["stale_rate_max_exclusive"]
            if stale_rate is not None
            else None
        ),
        "duplicates": (
            duplicate_rate < POC_THRESHOLDS["duplicate_rate_max_exclusive"]
            if duplicate_rate is not None
            else None
        ),
        "source_types": source_types >= POC_THRESHOLDS["source_types_min"],
        "relevance": (
            relevance_rate >= POC_THRESHOLDS["relevance_rate_min"]
            if relevance_rate is not None
            else None
        ),
        "merchant_onboarding": (
            merchant_onboarding_count <= POC_THRESHOLDS["merchant_onboarding_max"]
            if merchant_onboarding_count is not None
            else None
        ),
    }

    complete = not reasons and all(value is not None for value in gates.values())
    accepted = complete
    passed = complete and all(value is True for value in gates.values())

    return DailyMeasurement(
        accepted=accepted,
        passed=passed,
        complete=complete,
        gates=gates,
        metrics={
            "candidate_count": candidate_count,
            "ranked_count": ranked_count,
            "failed_count": failed_count,
            "useful_discoveries": audit.useful_discoveries,
            "valid_open_sample": audit.valid_open_sample,
            "valid_open_count": audit.valid_open_count,
            "valid_rate": valid_rate,
            "stale_count": expired_count,
            "stale_rate": stale_rate,
            "duplicate_count": duplicate_count,
            "duplicate_rate": duplicate_rate,
            "source_types": source_types,
            "relevance_sample": audit.relevance_sample,
            "relevant_count": audit.relevant_count,
            "relevance_rate": relevance_rate,
            "merchant_onboarding_count": merchant_onboarding_count,
        },
        reasons=tuple(reasons),
    )


def evaluate_window(records: Iterable[Mapping[str, object]]) -> dict[str, object]:
    rows = list(records)
    dates = [str(item.get("measurement_date") or "") for item in rows]
    unique_dates = {value for value in dates if value}

    reasons: list[str] = []
    if len(rows) != 14:
        reasons.append(f"expected 14 records, got {len(rows)}")
    if len(unique_dates) != len(rows):
        reasons.append("measurement dates must be unique and non-empty")

    rejected = [item for item in rows if item.get("accepted") is not True]
    failed = [item for item in rows if item.get("passed") is not True]
    if rejected:
        reasons.append(f"{len(rejected)} record(s) incomplete or invalid")
    if failed:
        reasons.append(f"{len(failed)} record(s) failed one or more POC gates")

    complete = len(rows) == 14 and len(unique_dates) == 14 and not rejected
    passed = complete and not failed
    return {
        "complete": complete,
        "passed": passed,
        "record_count": len(rows),
        "unique_day_count": len(unique_dates),
        "reasons": reasons,
    }


def _int_metric(metrics: Mapping[str, object], key: str) -> int:
    value = metrics.get(key, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _optional_int_metric(metrics: Mapping[str, object], key: str) -> int | None:
    if key not in metrics or metrics.get(key) is None:
        return None
    value = metrics.get(key)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _ratio(
    numerator: int | None,
    denominator: int | None,
    label: str,
    reasons: list[str],
) -> float | None:
    if numerator is None or denominator is None:
        reasons.append(f"{label} audit sample/count is required")
        return None
    if denominator <= 0:
        reasons.append(f"{label} sample must be > 0")
        return None
    if numerator < 0 or numerator > denominator:
        reasons.append(f"{label} count must be between 0 and sample")
        return None
    return numerator / denominator
