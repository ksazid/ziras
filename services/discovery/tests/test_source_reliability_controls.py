from pathlib import Path


def test_acquisition_retries_transient_failures_once():
    source = (Path(__file__).parents[1] / "src" / "ziras_discovery" / "acquisition.py").read_text()
    assert '"RETRY_ENABLED": True' in source
    assert '"RETRY_TIMES": 1' in source
    assert '"RETRY_HTTP_CODES": [408, 429, 500, 502, 503, 504]' in source


def test_pipeline_records_source_coverage_gate_input():
    source = (Path(__file__).parents[1] / "src" / "ziras_discovery" / "pipeline.py").read_text()
    assert 'metrics["contributing_source_count"] = contributing_source_count' in source
    assert 'metrics["source_coverage_ok"] = contributing_source_count >= 5' in source
