from ziras_discovery.poc_metrics import AuditCounts, evaluate_daily, evaluate_window


def _source_results(count: int = 5):
    return [
        {"source_key": f"source-{index}", "status": "ok", "candidate_count": 10}
        for index in range(count)
    ]


def _metrics(**overrides):
    values = {
        "candidate_count": 100,
        "ranked_count": 90,
        "failed_count": 0,
        "duplicate_count": 4,
        "expired_count": 4,
    }
    values.update(overrides)
    return values


def _audit(**overrides):
    values = {
        "useful_discoveries": 50,
        "valid_open_sample": 20,
        "valid_open_count": 18,
        "relevance_sample": 20,
        "relevant_count": 14,
        "merchant_onboarding_count": 0,
    }
    values.update(overrides)
    return AuditCounts(**values)


def test_daily_measurement_passes_all_thresholds():
    result = evaluate_daily(
        ingestion_status="completed",
        ingestion_metrics=_metrics(),
        source_results=_source_results(),
        audit=_audit(),
    )

    assert result.accepted is True
    assert result.complete is True
    assert result.passed is True
    assert all(result.gates.values())


def test_complete_failed_day_is_kept_as_accepted_evidence():
    result = evaluate_daily(
        ingestion_status="completed",
        ingestion_metrics=_metrics(),
        source_results=_source_results(),
        audit=_audit(useful_discoveries=49),
    )

    assert result.accepted is True
    assert result.complete is True
    assert result.passed is False
    assert result.gates["useful_discoveries"] is False


def test_missing_human_audit_fails_closed():
    result = evaluate_daily(
        ingestion_status="completed",
        ingestion_metrics=_metrics(),
        source_results=_source_results(),
        audit=AuditCounts(merchant_onboarding_count=0),
    )

    assert result.accepted is False
    assert result.complete is False
    assert result.passed is False
    assert "useful_discoveries audit is required" in result.reasons


def test_threshold_boundaries_are_exact():
    stale_fail = evaluate_daily(
        ingestion_status="completed",
        ingestion_metrics=_metrics(expired_count=5),
        source_results=_source_results(),
        audit=_audit(),
    )
    duplicate_fail = evaluate_daily(
        ingestion_status="completed",
        ingestion_metrics=_metrics(duplicate_count=5),
        source_results=_source_results(),
        audit=_audit(),
    )

    assert stale_fail.gates["stale_expired"] is False
    assert duplicate_fail.gates["duplicates"] is False


def test_five_distinct_sources_required():
    result = evaluate_daily(
        ingestion_status="completed",
        ingestion_metrics=_metrics(),
        source_results=_source_results(4),
        audit=_audit(),
    )

    assert result.accepted is True
    assert result.passed is False
    assert result.gates["source_types"] is False


def test_fourteen_complete_passing_days_pass_window():
    records = [
        {
            "measurement_date": f"2026-09-{day:02d}",
            "accepted": True,
            "passed": True,
        }
        for day in range(1, 15)
    ]

    result = evaluate_window(records)
    assert result["complete"] is True
    assert result["passed"] is True


def test_window_cannot_drop_a_complete_failed_day():
    records = [
        {
            "measurement_date": f"2026-09-{day:02d}",
            "accepted": True,
            "passed": day != 7,
        }
        for day in range(1, 15)
    ]

    result = evaluate_window(records)
    assert result["complete"] is True
    assert result["passed"] is False
    assert any("failed one or more POC gates" in reason for reason in result["reasons"])


def test_window_requires_fourteen_unique_accepted_days():
    records = [
        {"measurement_date": "2026-09-01", "accepted": True, "passed": True}
        for _ in range(14)
    ]

    result = evaluate_window(records)
    assert result["complete"] is False
    assert result["passed"] is False
