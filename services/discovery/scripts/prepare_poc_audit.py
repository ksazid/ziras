from __future__ import annotations

import argparse
import json
from pathlib import Path

from ziras_discovery.poc_audit import build_audit_template


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ingestion-json", required=True)
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.ingestion_json).read_text(encoding="utf-8"))
    template = build_audit_template(payload, sample_size=args.sample_size)
    text = json.dumps(template, indent=2, sort_keys=True)
    Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
