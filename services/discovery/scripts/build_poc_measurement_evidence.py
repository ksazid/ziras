from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path

from ziras_discovery.poc_metrics import AuditCounts, evaluate_daily


AUDIT_METHOD = "VS07-AUDIT-METHOD-V1"


def _sample(ranked: list[dict[str, object]], measured_sha: str) -> list[str]:
    if not ranked:
        return []
    target = len(ranked) if len(ranked) < 20 else min(30, max(20, math.ceil(len(ranked) * 0.20)))
    scored = []
    for item in ranked:
        discovery_id = str(item.get("id") or "")
        source_key = str(item.get("source_key") or "")
        score = sha256(f"{measured_sha}|{discovery_id}".encode()).hexdigest()
        scored.append((score, source_key, discovery_id))
    scored.sort()

    selected: list[tuple[str, str, str]] = []
    seen_sources: set[str] = set()
    for row in scored:
        if row[1] not in seen_sources:
            selected.append(row)
            seen_sources.add(row[1])
    selected_ids = {row[2] for row in selected[:target]}
    if len(selected_ids) < target:
        for row in scored:
            if len(selected_ids) >= target:
                break
            selected_ids.add(row[2])
    return [row[2] for row in scored if row[2] in selected_ids][:target]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingestion", default="poc-ingestion.json")
    parser.add_argument("--provenance", default="poc-run-provenance.json")
    parser.add_argument("--output", default="poc-measurement-evidence.json")
    args = parser.parse_args()

    ingestion = json.loads(Path(args.ingestion).read_text(encoding="utf-8"))
    provenance = json.loads(Path(args.provenance).read_text(encoding="utf-8"))
    measured_sha = str(provenance["github_sha"])
    ranked = list(ingestion.get("ranked") or [])
    source_results = list(ingestion.get("source_results") or [])
    audit = AuditCounts(merchant_onboarding_count=0)
    measurement = evaluate_daily(
        ingestion_status=str(ingestion.get("status") or "missing"),
        ingestion_metrics=dict(ingestion.get("metrics") or {}),
        source_results=source_results,
        audit=audit,
    )
    record = {
        "schema_version": 1,
        "evidence_kind": "vs07-daily-measurement",
        "audit_method": AUDIT_METHOD,
        "measurement_date": str(provenance.get("measurement_date") or ""),
        "github_run_id": str(provenance["github_run_id"]),
        "measured_sha": measured_sha,
        "trigger_type": str(provenance.get("trigger_type") or ""),
        "ingestion_status": ingestion.get("status"),
        "machine_metrics": ingestion.get("metrics") or {},
        "source_results": source_results,
        "valid_open_sample_ids": _sample(ranked, measured_sha),
        "audit": {
            "useful_discoveries": None,
            "valid_open_sample": None,
            "valid_open_count": None,
            "relevance_sample": None,
            "relevant_count": None,
            "merchant_onboarding_count": 0,
            "status": "pending",
        },
        "gates": dict(measurement.gates),
        "accepted": measurement.accepted,
        "passed": measurement.passed,
        "complete": measurement.complete,
        "reasons": list(measurement.reasons),
        "note": "Machine gates are computed immediately. Audit-dependent gates remain PENDING until frozen-method audit evidence is completed; missing audit evidence fails closed.",
    }
    Path(args.output).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
