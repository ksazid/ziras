from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from typing import Mapping, Sequence
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from .domain import Discovery, FreshnessState, SourceObservation, SourcePolicy, SourcePolicyScope


@dataclass(frozen=True, slots=True)
class PersistenceDelta:
    observation_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    duplicate_count: int = 0
    expired_count: int = 0


@dataclass(frozen=True, slots=True)
class SourceRunResult:
    source_key: str
    status: str
    source_url: str | None = None
    fetch_mode: str | None = None
    observed_at: datetime | None = None
    http_status: int | None = None
    candidate_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    duplicate_count: int = 0
    expired_count: int = 0
    error_code: str | None = None
    detail: str | None = None


class PostgresIngestionStore:
    """Direct PostgreSQL persistence for the POC ingestion slice."""

    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection

    def upsert_policy(self, policy: SourcePolicy) -> None:
        self.connection.execute(
            """
            INSERT INTO source_policy(
                source_key, access_mode, reason, policy_url, robots_required, reviewed_at,
                policy_scope, allowed_path_prefixes, max_requests_per_hour,
                attribution_required, content_storage_allowed, updated_at
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
            ON CONFLICT (source_key) DO UPDATE SET
                access_mode = EXCLUDED.access_mode,
                reason = EXCLUDED.reason,
                policy_url = EXCLUDED.policy_url,
                robots_required = EXCLUDED.robots_required,
                reviewed_at = EXCLUDED.reviewed_at,
                policy_scope = EXCLUDED.policy_scope,
                allowed_path_prefixes = EXCLUDED.allowed_path_prefixes,
                max_requests_per_hour = EXCLUDED.max_requests_per_hour,
                attribution_required = EXCLUDED.attribution_required,
                content_storage_allowed = EXCLUDED.content_storage_allowed,
                updated_at = now()
            """,
            (
                policy.source_key,
                policy.mode.value,
                policy.reason,
                policy.policy_url,
                policy.robots_required,
                policy.reviewed_at,
                policy.scope.value,
                list(policy.allowed_path_prefixes),
                policy.max_requests_per_hour,
                policy.attribution_required,
                policy.content_storage_allowed,
            ),
        )

    def begin_run(self, scope: SourcePolicyScope, *, started_at: datetime) -> UUID:
        run_id = uuid4()
        self.connection.execute(
            """
            INSERT INTO ingestion_run(id, policy_scope, started_at, status)
            VALUES (%s, %s, %s, 'running')
            """,
            (run_id, scope.value, _utc(started_at)),
        )
        return run_id

    def request_count_last_hour(self, source_key: str, *, now: datetime) -> int:
        since = _utc(now) - timedelta(hours=1)
        row = self.connection.execute(
            """
            SELECT count(*)
            FROM ingestion_source_result
            WHERE source_key = %s
              AND status = 'ok'
              AND observed_at >= %s
            """,
            (source_key, since),
        ).fetchone()
        return int(row[0]) if row else 0

    def persist_normalized(
        self,
        *,
        run_id: UUID,
        policy: SourcePolicy,
        observation: SourceObservation,
        discoveries: Sequence[Discovery],
    ) -> PersistenceDelta:
        self.upsert_policy(policy)
        self.connection.execute(
            """
            INSERT INTO source_observation(
                id, source_key, source_url, observed_at, content_hash,
                adapter, http_status, extracted
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                observation.id,
                observation.source_key,
                observation.source_url,
                _utc(observation.observed_at),
                observation.content_hash,
                observation.adapter,
                observation.http_status,
                Jsonb(_jsonable(dict(observation.extracted))),
            ),
        )
        self.connection.execute(
            "SELECT promote_source_state(%s,%s,%s)",
            (observation.source_key, observation.id, _utc(observation.observed_at)),
        )

        inserted = 0
        updated = 0
        duplicates = 0
        expired = 0
        for discovery in discoveries:
            dedupe_key = discovery_fingerprint(discovery)
            row = self.connection.execute(
                """
                INSERT INTO discovery(
                    id, discovery_type, entity_id, source_key, source_url, title,
                    observed_at, starts_at, expires_at, original_price, current_price,
                    currency, freshness_state, dedupe_key, first_seen_at, last_seen_at,
                    seen_count, last_ingestion_run_id
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s)
                ON CONFLICT (dedupe_key) WHERE dedupe_key IS NOT NULL DO UPDATE SET
                    entity_id = COALESCE(EXCLUDED.entity_id, discovery.entity_id),
                    source_key = CASE
                        WHEN EXCLUDED.observed_at >= discovery.observed_at THEN EXCLUDED.source_key
                        ELSE discovery.source_key
                    END,
                    source_url = CASE
                        WHEN EXCLUDED.observed_at >= discovery.observed_at THEN EXCLUDED.source_url
                        ELSE discovery.source_url
                    END,
                    title = CASE
                        WHEN EXCLUDED.observed_at >= discovery.observed_at THEN EXCLUDED.title
                        ELSE discovery.title
                    END,
                    observed_at = GREATEST(discovery.observed_at, EXCLUDED.observed_at),
                    starts_at = COALESCE(EXCLUDED.starts_at, discovery.starts_at),
                    expires_at = COALESCE(EXCLUDED.expires_at, discovery.expires_at),
                    original_price = COALESCE(EXCLUDED.original_price, discovery.original_price),
                    current_price = COALESCE(EXCLUDED.current_price, discovery.current_price),
                    currency = COALESCE(EXCLUDED.currency, discovery.currency),
                    freshness_state = CASE
                        WHEN EXCLUDED.observed_at >= discovery.observed_at THEN EXCLUDED.freshness_state
                        ELSE discovery.freshness_state
                    END,
                    last_seen_at = GREATEST(discovery.last_seen_at, EXCLUDED.last_seen_at),
                    seen_count = discovery.seen_count + 1,
                    last_ingestion_run_id = EXCLUDED.last_ingestion_run_id,
                    updated_at = now()
                RETURNING id, (xmax = 0) AS inserted
                """,
                (
                    discovery.id,
                    discovery.discovery_type.value,
                    discovery.entity_id,
                    discovery.source_key,
                    discovery.source_url,
                    discovery.title,
                    _utc(discovery.observed_at),
                    _utc(discovery.starts_at) if discovery.starts_at else None,
                    _utc(discovery.expires_at) if discovery.expires_at else None,
                    discovery.original_price,
                    discovery.current_price,
                    discovery.currency,
                    discovery.freshness.value,
                    dedupe_key,
                    _utc(discovery.observed_at),
                    _utc(discovery.observed_at),
                    run_id,
                ),
            ).fetchone()
            persisted_id = row[0]
            was_inserted = bool(row[1])
            if was_inserted:
                inserted += 1
            else:
                updated += 1
                duplicates += 1
            if discovery.freshness is FreshnessState.EXPIRED:
                expired += 1
            self._insert_evidence(
                discovery_id=persisted_id,
                observation=observation,
                discovery=discovery,
            )

        return PersistenceDelta(
            observation_count=1,
            inserted_count=inserted,
            updated_count=updated,
            duplicate_count=duplicates,
            expired_count=expired,
        )

    def _insert_evidence(
        self,
        *,
        discovery_id: UUID,
        observation: SourceObservation,
        discovery: Discovery,
    ) -> None:
        values: list[tuple[str, str, float]] = [("title", discovery.title, 0.9)]
        if discovery.current_price is not None:
            values.append(("current_price", str(discovery.current_price), 0.9))
        if discovery.original_price is not None:
            values.append(("original_price", str(discovery.original_price), 0.9))
        if discovery.starts_at is not None:
            values.append(("starts_at", _utc(discovery.starts_at).isoformat(), 0.9))
        if discovery.expires_at is not None:
            values.append(("expires_at", _utc(discovery.expires_at).isoformat(), 0.9))

        for field_name, raw_value, confidence in values:
            self.connection.execute(
                """
                INSERT INTO discovery_evidence(
                    discovery_id, source_observation_id, field_name, raw_value,
                    confidence, observed_at
                )
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (
                    discovery_id,
                    observation.id,
                    field_name,
                    raw_value,
                    confidence,
                    _utc(observation.observed_at),
                ),
            )

    def record_source_result(self, run_id: UUID, result: SourceRunResult) -> None:
        self.connection.execute(
            """
            INSERT INTO ingestion_source_result(
                run_id, source_key, source_url, fetch_mode, status, observed_at,
                http_status, candidate_count, inserted_count, updated_count,
                duplicate_count, expired_count, error_code, detail
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                run_id,
                result.source_key,
                result.source_url,
                result.fetch_mode,
                result.status,
                _utc(result.observed_at) if result.observed_at else None,
                result.http_status,
                result.candidate_count,
                result.inserted_count,
                result.updated_count,
                result.duplicate_count,
                result.expired_count,
                result.error_code,
                result.detail,
            ),
        )

    def finalize_run(
        self,
        run_id: UUID,
        *,
        completed_at: datetime,
        status: str,
        metrics: Mapping[str, object],
    ) -> None:
        self.connection.execute(
            """
            UPDATE ingestion_run
            SET completed_at = %s,
                status = %s,
                source_count = %s,
                blocked_count = %s,
                failed_count = %s,
                observation_count = %s,
                candidate_count = %s,
                inserted_count = %s,
                updated_count = %s,
                duplicate_count = %s,
                expired_count = %s,
                ranked_count = %s,
                metrics = %s
            WHERE id = %s
            """,
            (
                _utc(completed_at),
                status,
                int(metrics.get("source_count", 0)),
                int(metrics.get("blocked_count", 0)),
                int(metrics.get("failed_count", 0)),
                int(metrics.get("observation_count", 0)),
                int(metrics.get("candidate_count", 0)),
                int(metrics.get("inserted_count", 0)),
                int(metrics.get("updated_count", 0)),
                int(metrics.get("duplicate_count", 0)),
                int(metrics.get("expired_count", 0)),
                int(metrics.get("ranked_count", 0)),
                Jsonb(_jsonable(dict(metrics))),
                run_id,
            ),
        )


def discovery_fingerprint(discovery: Discovery) -> str:
    """Conservative content identity used before canonical-entity resolution is available.

    Exact title/type/value/date matches can dedupe across sources. Source URL/key are deliberately
    omitted so equivalent syndicated records can collapse; differing price/date attributes prevent
    common generic-title collisions.
    """

    normalized_title = re.sub(r"[^a-z0-9]+", " ", discovery.title.casefold()).strip()
    parts = [
        "v1",
        discovery.discovery_type.value,
        normalized_title,
        str(discovery.entity_id or ""),
        _decimal_key(discovery.original_price),
        _decimal_key(discovery.current_price),
        (discovery.currency or "").upper(),
        _datetime_key(discovery.starts_at),
        _datetime_key(discovery.expires_at),
    ]
    return sha256("|".join(parts).encode("utf-8")).hexdigest()


def _decimal_key(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _datetime_key(value: datetime | None) -> str:
    if value is None:
        return ""
    return _utc(value).replace(microsecond=0).isoformat()


def _jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return _utc(value).isoformat()
    if isinstance(value, UUID):
        return str(value)
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
