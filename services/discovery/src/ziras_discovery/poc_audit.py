from __future__ import annotations

from collections import defaultdict, deque
from typing import Mapping, Sequence

from .poc_metrics import AuditCounts


AUDIT_SCHEMA_VERSION = 1
DEFAULT_SAMPLE_SIZE = 30


def build_audit_template(
    ingestion: Mapping[str, object],
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> dict[str, object]:
    ranked = [dict(item) for item in _mapping_sequence(ingestion.get("ranked"))]
    metrics = dict(ingestion.get("metrics") or {})
    sample = _stratified_sample(ranked, max(1, sample_size))

    return {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "ingestion_run_id": str(ingestion.get("run_id") or ""),
        "ingestion_status": str(ingestion.get("status") or ""),
        "interest_profile": None,
        "reviewer": None,
        "reviewed_at": None,
        "machine_evidence": {
            "candidate_count": metrics.get("candidate_count"),
            "ranked_count": metrics.get("ranked_count"),
            "duplicate_count": metrics.get("duplicate_count"),
            "expired_count": metrics.get("expired_count"),
            "merchant_onboarding_count": metrics.get("merchant_onboarding_count"),
        },
        "useful_review": [
            {
                **_review_identity(item),
                "useful": None,
                "review_note": None,
            }
            for item in ranked
        ],
        "validity_relevance_sample": [
            {
                **_review_identity(item),
                "valid_when_opened": None,
                "relevant": None,
                "review_note": None,
            }
            for item in sample
        ],
        "sampling": {
            "method": "deterministic-round-robin-by-source-class-then-source-key",
            "requested_size": sample_size,
            "actual_size": len(sample),
            "ranked_inventory_serialized": len(ranked),
        },
        "instructions": [
            "Set interest_profile before judging relevance; do not infer a profile from the discoveries.",
            "Review every useful_review item and set useful to true or false.",
            "Open each validity_relevance_sample source_url and set valid_when_opened true or false.",
            "Judge each validity_relevance_sample item against interest_profile and set relevant true or false.",
            "Do not edit machine_evidence; it comes from the ingestion run.",
        ],
    }


def audit_counts_from_template(template: Mapping[str, object]) -> AuditCounts:
    useful_rows = [dict(item) for item in _mapping_sequence(template.get("useful_review"))]
    sample_rows = [
        dict(item)
        for item in _mapping_sequence(template.get("validity_relevance_sample"))
    ]
    machine = dict(template.get("machine_evidence") or {})

    if not useful_rows:
        raise ValueError("useful_review must contain at least one discovery")
    if not sample_rows:
        raise ValueError("validity_relevance_sample must contain at least one discovery")
    if not template.get("interest_profile"):
        raise ValueError("interest_profile is required before relevance review")

    useful = _required_bool_count(useful_rows, "useful")
    valid = _required_bool_count(sample_rows, "valid_when_opened")
    relevant = _required_bool_count(sample_rows, "relevant")
    merchant_onboarding_count = _optional_int(machine.get("merchant_onboarding_count"))
    if merchant_onboarding_count is None:
        raise ValueError("machine merchant_onboarding_count evidence is required")

    return AuditCounts(
        useful_discoveries=useful,
        valid_open_sample=len(sample_rows),
        valid_open_count=valid,
        relevance_sample=len(sample_rows),
        relevant_count=relevant,
        merchant_onboarding_count=merchant_onboarding_count,
    )


def _stratified_sample(
    ranked: Sequence[Mapping[str, object]],
    sample_size: int,
) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], deque[dict[str, object]]] = defaultdict(deque)
    for raw in ranked:
        item = dict(raw)
        source_class = str(item.get("source_class") or "unknown")
        source_key = str(item.get("source_key") or "unknown")
        groups[(source_class, source_key)].append(item)

    ordered_keys = sorted(groups)
    result: list[dict[str, object]] = []
    while ordered_keys and len(result) < min(sample_size, len(ranked)):
        next_keys: list[tuple[str, str]] = []
        for key in ordered_keys:
            queue = groups[key]
            if queue and len(result) < sample_size:
                result.append(queue.popleft())
            if queue:
                next_keys.append(key)
        ordered_keys = next_keys
    return result


def _review_identity(item: Mapping[str, object]) -> dict[str, object]:
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "type": item.get("type"),
        "source_key": item.get("source_key"),
        "source_class": item.get("source_class"),
        "source_url": item.get("source_url"),
        "freshness": item.get("freshness"),
    }


def _required_bool_count(rows: Sequence[Mapping[str, object]], key: str) -> int:
    values = [row.get(key) for row in rows]
    if any(not isinstance(value, bool) for value in values):
        raise ValueError(f"every {key} label must be true or false")
    return sum(1 for value in values if value is True)


def _mapping_sequence(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
