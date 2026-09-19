from ziras_discovery.poc_metrics import AuditCounts, evaluate_daily, evaluate_window


def _audit():
    return AuditCounts(
        useful_discoveries=50,
        valid_open_sample=20,
        valid_open_count=18,
        relevance_sample=20,
        relevant_count=14,
        merchant_onboarding_count=0,
    )


def test_source_gate_counts_independent_source_classes_not_source_keys():
    results = [
        {"source_key": "a", "source_class": "official_event", "status": "ok", "candidate_count": 10},
        {"source_key": "b", "source_class": "official_event", "status": "ok", "candidate_count": 10},
        {"source_key": "c", "source_class": "official_retail", "status": "ok", "candidate_count": 10},
        {"source_key": "d", "source_class": "official_culture", "status": "ok", "candidate_count": 10},
        {"source_key": "e", "source_class": "official_family", "status": "ok", "candidate_count": 10},
    ]
    measurement = evaluate_daily(
        ingestion_status="completed",
        ingestion_metrics={"candidate_count": 50, "ranked_count": 50, "duplicate_count": 0, "expired_count": 0, "failed_count": 0},
        source_results=results,
        audit=_audit(),
    )
    assert measurement.metrics["source_types"] == 4
    assert measurement.gates["source_types"] is False


def test_window_requires_consecutive_days_and_run_sha_provenance():
    records = [
        {
            "measurement_date": f"2026-10-{day:02d}",
            "github_run_id": str(day),
            "measured_sha": "a" * 40,
            "accepted": True,
            "passed": True,
        }
        for day in range(1, 15)
    ]
    assert evaluate_window(records)["passed"] is True
    records[7]["measurement_date"] = "2026-10-20"
    result = evaluate_window(records)
    assert result["passed"] is False
    assert any("consecutive" in reason for reason in result["reasons"])
    records[7]["measurement_date"] = "2026-10-08"
    records[3]["measured_sha"] = ""
    result = evaluate_window(records)
    assert result["passed"] is False
    assert any("provenance" in reason for reason in result["reasons"])
