from __future__ import annotations

import argparse
import json
from pathlib import Path

from ziras_discovery.poc_metrics import evaluate_window


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args()

    records = [json.loads(Path(path).read_text(encoding="utf-8")) for path in args.records]
    result = evaluate_window(records)
    payload = {
        "schema_version": 1,
        **result,
        "records": [
            {
                "measurement_date": item.get("measurement_date"),
                "github_sha": item.get("github_sha"),
                "github_run_id": item.get("github_run_id"),
                "accepted": item.get("accepted"),
                "passed": item.get("passed"),
                "gates": item.get("gates"),
            }
            for item in sorted(records, key=lambda row: str(row.get("measurement_date") or ""))
        ],
    }
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
