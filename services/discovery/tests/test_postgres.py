from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest


DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL is required for PostgreSQL integration tests")
def test_migration_and_monotonic_source_state() -> None:
    migration = Path(__file__).parents[1] / "migrations" / "001_discovery_kernel.sql"
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        connection.execute(migration.read_text())

        extension_names = {
            row[0]
            for row in connection.execute(
                "SELECT extname FROM pg_extension WHERE extname IN ('postgis','vector')"
            ).fetchall()
        }
        assert extension_names == {"postgis", "vector"}

        source_key = f"fixture-{uuid4()}"
        first_id = uuid4()
        old_id = uuid4()
        new_id = uuid4()
        now = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

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
                (observation_id, source_key, "https://example.com", observed_at, str(observation_id)),
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
