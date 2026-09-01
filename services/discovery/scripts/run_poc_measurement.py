from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

from ziras_discovery.poc_audit import audit_counts_from_template
from ziras_discovery.poc_metrics import AuditCounts, evaluate_daily


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingestion-json", required=True)
    parser.add_argument("--audit-json")
    parser.add_argument("--measurement-date", default=date.today().isoformat())
    parser.add_argument("--github-sha", required=True)
    parser.add_argument("--github-run-id", required=True)
    parser.add_argument("--useful-discoveries", type=int)
    parser.add_argument("--valid-open-sample", type=int)
    parser.add_argument("--valid-open-count", type=int)
    parser.add_argument("--relevance-sample", type=int)
    parser.add_argument("--relevant-count", type=int)
    parser.add_argument("--merchant-onboarding-count", type=int)
    parser.add_argument("--output")
    args = parser.parse_args()

    payload = json.loads(Path(args.ingestion_json).read_text(encoding="utf-8"))
    if args.audit_json:
        audit_template = json.loads(Path(args.audit_json).read_text(encoding="utf-8"))
        try:
            audit = audit_counts_from_template(audit_template)
        except ValueError as exc:
            print(json.dumps({"accepted": False, "error": str(exc)}, indent=2))
            return 2
    else:
        audit = AuditCounts(
            useful_discoveries=args.useful_discoveries,
            valid_open_sample=args.valid_open_sample,
            valid_open_count=args.valid_open_count,
            relevance_sample=args.relevance_sample,
            relevant_count=args.relevant_count,
            merchant_onboarding_count=args.merchant_onboarding_count,
        )

    measurement = evaluate_daily(
        ingestion_status=str(payload.get("status") or ""),
        ingestion_metrics=payload.get("metrics") or {},
        source_results=payload.get("source_results") or [],
        audit=audit,
    )

    result = {
        "schema_version": 1,
        "measurement_date": args.measurement_date,
        "github_sha": args.github_sha,
        "github_run_id": str(args.github_run_id),
        "ingestion_run_id": str(payload.get("run_id") or ""),
        "accepted": measurement.accepted,
        "complete": measurement.complete,
        "passed": measurement.passed,
        "gates": dict(measurement.gates),
        "metrics": dict(measurement.metrics),
        "reasons": list(measurement.reasons),
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)

    # Incomplete evidence is an execution failure; a complete day that misses a
    # product threshold remains valid evidence and therefore exits successfully.
    return 0 if measurement.accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
