from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import UUID

import psycopg

from ziras_discovery.acquisition import ScrapyPlaywrightAcquirer
from ziras_discovery.domain import SourcePolicyScope
from ziras_discovery.persistence import PostgresIngestionStore
from ziras_discovery.pipeline import PocIngestionPipeline
from ziras_discovery.ranking import DeterministicRanker
from ziras_discovery.source_catalog import build_policy_registry, load_source_catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("research", "poc"), default="poc")
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--apply-migrations", action="store_true")
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")

    entries = load_source_catalog()
    registry = build_policy_registry(entries)
    scope = SourcePolicyScope(args.scope)

    with psycopg.connect(args.database_url, autocommit=True) as connection:
        if args.apply_migrations:
            _apply_migrations(connection)
        store = PostgresIngestionStore(connection)
        pipeline = PocIngestionPipeline(
            entries=entries,
            policy_registry=registry,
            acquisition=ScrapyPlaywrightAcquirer(),
            store=store,
            ranker=DeterministicRanker(),
        )
        summary = pipeline.run(
            scope=scope,
            source_keys=tuple(args.source),
            now=datetime.now(timezone.utc),
        )
        source_results = _load_source_results(connection, summary.run_id)

    payload = {
        "run_id": str(summary.run_id),
        "status": summary.status,
        "scope": scope.value,
        "metrics": dict(summary.metrics),
        "source_results": source_results,
        "ranked": [
            {
                "id": str(item.id),
                "type": item.discovery_type.value,
                "title": item.title,
                "source_key": item.source_key,
                "source_url": item.source_url,
                "freshness": item.freshness.value,
                "starts_at": item.starts_at.isoformat() if item.starts_at else None,
                "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                "original_price": str(item.original_price) if item.original_price is not None else None,
                "current_price": str(item.current_price) if item.current_price is not None else None,
                "currency": item.currency,
            }
            for item in summary.ranked[:100]
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if summary.status in {"completed", "partial"} else 1


def _load_source_results(connection: psycopg.Connection, run_id: UUID) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT source_key, source_url, fetch_mode, status, observed_at, http_status,
               candidate_count, inserted_count, updated_count, duplicate_count,
               expired_count, error_code, detail
        FROM ingestion_source_result
        WHERE run_id = %s
        ORDER BY id
        """,
        (run_id,),
    ).fetchall()
    results: list[dict[str, object]] = []
    for row in rows:
        results.append(
            {
                "source_key": row[0],
                "source_url": row[1],
                "fetch_mode": row[2],
                "status": row[3],
                "observed_at": row[4].isoformat() if row[4] else None,
                "http_status": row[5],
                "candidate_count": row[6],
                "inserted_count": row[7],
                "updated_count": row[8],
                "duplicate_count": row[9],
                "expired_count": row[10],
                "error_code": row[11],
                "detail": row[12],
            }
        )
    return results


def _apply_migrations(connection: psycopg.Connection) -> None:
    migration_dir = Path(__file__).parents[1] / "migrations"
    for migration in sorted(migration_dir.glob("*.sql")):
        connection.execute(migration.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
