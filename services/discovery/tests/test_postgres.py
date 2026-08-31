from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from ziras_discovery.domain import (
    Discovery,
    DiscoveryType,
    FreshnessState,
    SourceAccessMode,
    SourceObservation,
    SourcePolicy,
    SourcePolicyScope,
)
from ziras_discovery.persistence import PostgresIngestionStore, SourceRunResult


DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _apply_migrations(connection: psycopg.Connection) -> None:
    migration_dir = Path(__file__).parents[1] / "migrations"
    for migration in sorted(migration_dir.glob("*.sql")):
        connection.execute(migration.read_text())


@pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is required for PostgreSQL integration tests")
def test_migration_and_monotonic_source_state() -> None:
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        _apply_migrations(connection)

        extension_names = {
            row[0]
            for row in connection.execute(
                "SELECT extname FROM pg_extension WHERE extname IN ('postgis','vector')"
            ).fetchall()
        }
        assert extension_names == {"postgis", "vector"}

        policy_columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'source_policy'
                """
            ).fetchall()
        }
        assert {
            "policy_scope",
            "allowed_path_prefixes",
            "max_requests_per_hour",
            "attribution_required",
            "content_storage_allowed",
        }.issubset(policy_columns)

        discovery_columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'discovery'
                """
            ).fetchall()
        }
        assert {
            "dedupe_key",
            "first_seen_at",
            "last_seen_at",
            "seen_count",
            "last_ingestion_run_id",
        }.issubset(discovery_columns)

        ingestion_tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('ingestion_run','ingestion_source_result')
                """
            ).fetchall()
        }
        assert ingestion_tables == {"ingestion_run", "ingestion_source_result"}

        source_key = f"fixture-{uuid4()}"
        first_id = uuid4()
        old_id = uuid4()
        new_id = uuid4()
        now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            connection.execute(
                """
                INSERT INTO source_observation(id, source_key, source_url, observed_at, content_hash, extracted)
                VALUES (%s, %s, %s, %s, %s, '{}'::jsonb)
                """,
                (uuid4(), source_key, "https://example.com", now, "denied"),
            )

        connection.execute(
            """
            INSERT INTO source_policy(
                source_key, access_mode, reason, policy_scope, allowed_path_prefixes,
                max_requests_per_hour, attribution_required, content_storage_allowed
            )
            VALUES (%s, 'allow', 'Fixture policy approved for integration test', 'poc', ARRAY['/offers'], 2, true, false)
            """,
            (source_key,),
        )

        stored_policy = connection.execute(
            """
            SELECT policy_scope, allowed_path_prefixes, max_requests_per_hour,
                   attribution_required, content_storage_allowed
            FROM source_policy WHERE source_key = %s
            """,
            (source_key,),
        ).fetchone()
        assert stored_policy == ("poc", ["/offers"], 2, True, False)

        for observation_id, observed_at in (
            (first_id, now),
            (old_id, now - timedelta(minutes=1)),
            (new_id, now + timedelta(minutes=1)),
        ):
            connection.execute(
                """
                INSERT INTO source_observation(id, source_key, source_url, observed_at, content_hash, extracted)
                VALUES (%s, %s, %s, %s, %s, '{}'::jsonb)
                """,
                (observation_id, source_key, "https://example.com/offers", observed_at, str(observation_id)),
            )

        assert connection.execute(
            "SELECT promote_source_state(%s, %s, %s)",
            (source_key, first_id, now),
        ).fetchone()[0] is True
        assert connection.execute(
            "SELECT promote_source_state(%s, %s, %s)",
            (source_key, old_id, now - timedelta(minutes=1)),
        ).fetchone()[0] is False
        assert connection.execute(
            "SELECT promote_source_state(%s, %s, %s)",
            (source_key, new_id, now + timedelta(minutes=1)),
        ).fetchone()[0] is True

        current = connection.execute(
            "SELECT observation_id, last_observed_at FROM source_state WHERE source_key = %s",
            (source_key,),
        ).fetchone()
        assert current[0] == new_id
        assert current[1] == now + timedelta(minutes=1)


@pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is required for PostgreSQL integration tests")
def test_postgis_and_pgvector_types_are_usable() -> None:
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        _apply_migrations(connection)

        distance = connection.execute(
            """
            SELECT ST_Distance(
                ST_SetSRID(ST_MakePoint(14.5146, 35.9110), 4326)::geography,
                ST_SetSRID(ST_MakePoint(14.5019, 35.8997), 4326)::geography
            )
            """
        ).fetchone()[0]
        assert 1000 < distance < 2500

        dimensions = connection.execute("SELECT vector_dims('[1,2,3]'::vector)").fetchone()[0]
        assert dimensions == 3


@pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is required for PostgreSQL integration tests")
def test_ingestion_store_is_idempotent_across_sources_and_records_provenance() -> None:
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        _apply_migrations(connection)
        store = PostgresIngestionStore(connection)
        now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

        policies = []
        for source_key in (f"source-a-{uuid4()}", f"source-b-{uuid4()}"):
            policy = SourcePolicy(
                source_key=source_key,
                mode=SourceAccessMode.ALLOW,
                reason="fixture POC policy",
                scope=SourcePolicyScope.POC,
                allowed_path_prefixes=("/offers",),
                max_requests_per_hour=2,
            )
            store.upsert_policy(policy)
            policies.append(policy)

        run_one = store.begin_run(SourcePolicyScope.POC, started_at=now)
        observation_one = SourceObservation(
            id=uuid4(),
            source_key=policies[0].source_key,
            source_url="https://a.example/offers/lamp",
            observed_at=now,
            content_hash="content-a",
            extracted={"candidate_count": 1},
            http_status=200,
            adapter="fixture",
        )
        discovery_one = Discovery(
            id=uuid4(),
            discovery_type=DiscoveryType.DEAL,
            entity_id=None,
            title="Desk Lamp",
            source_key=policies[0].source_key,
            source_url=observation_one.source_url,
            observed_at=now,
            expires_at=now + timedelta(days=5),
            current_price=Decimal("19.90"),
            currency="EUR",
            freshness=FreshnessState.LIKELY_LIVE,
        )
        delta_one = store.persist_normalized(
            run_id=run_one,
            policy=policies[0],
            observation=observation_one,
            discoveries=(discovery_one,),
        )
        store.record_source_result(
            run_one,
            SourceRunResult(
                source_key=policies[0].source_key,
                source_url=observation_one.source_url,
                fetch_mode="static",
                status="ok",
                observed_at=now,
                http_status=200,
                candidate_count=1,
                inserted_count=1,
            ),
        )
        store.finalize_run(
            run_one,
            completed_at=now + timedelta(seconds=1),
            status="completed",
            metrics={
                "source_count": 1,
                "observation_count": 1,
                "candidate_count": 1,
                "inserted_count": 1,
                "ranked_count": 1,
            },
        )

        run_two = store.begin_run(SourcePolicyScope.POC, started_at=now + timedelta(minutes=5))
        observation_two = SourceObservation(
            id=uuid4(),
            source_key=policies[1].source_key,
            source_url="https://b.example/offers/desk-lamp",
            observed_at=now + timedelta(minutes=5),
            content_hash="content-b",
            extracted={"candidate_count": 1},
            http_status=200,
            adapter="fixture",
        )
        discovery_two = Discovery(
            id=uuid4(),
            discovery_type=DiscoveryType.DEAL,
            entity_id=None,
            title="Desk Lamp",
            source_key=policies[1].source_key,
            source_url=observation_two.source_url,
            observed_at=now + timedelta(minutes=5),
            expires_at=now + timedelta(days=5),
            current_price=Decimal("19.90"),
            currency="EUR",
            freshness=FreshnessState.LIKELY_LIVE,
        )
        delta_two = store.persist_normalized(
            run_id=run_two,
            policy=policies[1],
            observation=observation_two,
            discoveries=(discovery_two,),
        )

        assert delta_one.inserted_count == 1
        assert delta_one.updated_count == 0
        assert delta_two.inserted_count == 0
        assert delta_two.updated_count == 1
        assert delta_two.duplicate_count == 1

        rows = connection.execute(
            """
            SELECT title, seen_count, source_key, first_seen_at, last_seen_at
            FROM discovery
            WHERE title = 'Desk Lamp'
            """
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][1] == 2
        assert rows[0][2] == policies[1].source_key
        assert rows[0][3] == now
        assert rows[0][4] == now + timedelta(minutes=5)

        evidence_count = connection.execute(
            """
            SELECT count(*)
            FROM discovery_evidence e
            JOIN discovery d ON d.id = e.discovery_id
            WHERE d.title = 'Desk Lamp' AND e.field_name = 'title'
            """
        ).fetchone()[0]
        assert evidence_count == 2

        run_count = connection.execute("SELECT count(*) FROM ingestion_run").fetchone()[0]
        assert run_count >= 2
