from __future__ import annotations

import pytest

from ziras_discovery.poc_audit import audit_counts_from_template, build_audit_template


def _ingestion() -> dict[str, object]:
    ranked = []
    for index in range(12):
        ranked.append(
            {
                "id": str(index),
                "title": f"Discovery {index}",
                "type": "deal",
                "source_key": f"source-{index % 4}",
                "source_class": f"class-{index % 3}",
                "source_url": f"https://example.com/{index}",
                "freshness": "unverified",
            }
        )
    return {
        "run_id": "run-1",
        "status": "completed",
        "metrics": {
            "candidate_count": 12,
            "ranked_count": 12,
            "duplicate_count": 0,
            "expired_count": 0,
            "merchant_onboarding_count": 0,
        },
        "ranked": ranked,
    }


def test_audit_template_is_deterministic_and_stratified() -> None:
    first = build_audit_template(_ingestion(), sample_size=6)
    second = build_audit_template(_ingestion(), sample_size=6)

    assert first == second
    assert len(first["useful_review"]) == 12
    sample = first["validity_relevance_sample"]
    assert len(sample) == 6
    assert len({row["source_class"] for row in sample[:3]}) == 3
    assert first["machine_evidence"]["merchant_onboarding_count"] == 0


def test_incomplete_audit_template_fails_closed() -> None:
    template = build_audit_template(_ingestion(), sample_size=4)
    template["interest_profile"] = "Family activities and local savings"

    with pytest.raises(ValueError, match="every useful label"):
        audit_counts_from_template(template)


def test_completed_audit_template_produces_counts() -> None:
    template = build_audit_template(_ingestion(), sample_size=4)
    template["interest_profile"] = "Family activities and local savings"
    template["reviewer"] = "pilot-reviewer"

    for index, row in enumerate(template["useful_review"]):
        row["useful"] = index < 10
    for index, row in enumerate(template["validity_relevance_sample"]):
        row["valid_when_opened"] = index < 4
        row["relevant"] = index < 3

    counts = audit_counts_from_template(template)
    assert counts.useful_discoveries == 10
    assert counts.valid_open_sample == 4
    assert counts.valid_open_count == 4
    assert counts.relevance_sample == 4
    assert counts.relevant_count == 3
    assert counts.merchant_onboarding_count == 0


def test_relevance_requires_explicit_interest_profile() -> None:
    template = build_audit_template(_ingestion(), sample_size=4)
    for row in template["useful_review"]:
        row["useful"] = True
    for row in template["validity_relevance_sample"]:
        row["valid_when_opened"] = True
        row["relevant"] = True

    with pytest.raises(ValueError, match="interest_profile"):
        audit_counts_from_template(template)
