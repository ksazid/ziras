from ziras_discovery.poc_metrics import AuditCounts, evaluate_daily


def test_repeat_observations_do_not_need_to_be_reported_as_poc_duplicates():
    metrics = {
        "candidate_count": 100,
        "ranked_count": 100,
        "failed_count": 0,
        "duplicate_count": 0,
        "repeat_seen_count": 100,
        "expired_count": 0,
    }
    sources = [
        {"source_key": f"source-{i}", "status": "ok", "candidate_count": 20}
        for i in range(5)
    ]
    audit = AuditCounts(
        useful_discoveries=100,
        valid_open_sample=20,
        valid_open_count=20,
        relevance_sample=100,
        relevant_count=100,
        merchant_onboarding_count=0,
    )
    result = evaluate_daily(
        ingestion_status="completed",
        ingestion_metrics=metrics,
        source_results=sources,
        audit=audit,
    )
    assert result.metrics["duplicate_count"] == 0
    assert result.gates["duplicates"] is True
