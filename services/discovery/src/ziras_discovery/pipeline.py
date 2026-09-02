from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Mapping, Sequence
from uuid import UUID

from .acquisition import AcquisitionBackend, AcquisitionRequest
from .adapters.public_web import PublicWebSignalAdapter, TextSignalConfig
from .adapters.structured_html import StructuredHtmlAdapter
from .domain import Discovery, DiscoveryType, FreshnessState, SourceAccessMode, SourcePolicyScope
from .freshness import FreshnessInput, classify_freshness
from .persistence import (
    PersistenceDelta,
    PostgresIngestionStore,
    SourceRunResult,
    discovery_fingerprint,
)
from .policy import SourcePolicyRegistry
from .ports import Ranker, SourceAdapter
from .source_catalog import AdapterKind, FetchMode, SourceCatalogEntry


@dataclass(frozen=True, slots=True)
class IngestionRunSummary:
    run_id: UUID
    status: str
    metrics: Mapping[str, object]
    ranked: tuple[Discovery, ...]


class PocIngestionPipeline:
    def __init__(
        self,
        *,
        entries: Sequence[SourceCatalogEntry],
        policy_registry: SourcePolicyRegistry,
        acquisition: AcquisitionBackend,
        store: PostgresIngestionStore,
        ranker: Ranker,
    ) -> None:
        self.entries = tuple(entries)
        self.policy_registry = policy_registry
        self.acquisition = acquisition
        self.store = store
        self.ranker = ranker

    def run(
        self,
        *,
        scope: SourcePolicyScope = SourcePolicyScope.POC,
        source_keys: Sequence[str] = (),
        now: datetime | None = None,
        rank_context: dict[str, object] | None = None,
    ) -> IngestionRunSummary:
        started_at = _utc(now or datetime.now(timezone.utc))
        selected_keys = set(source_keys)
        selected_entries = tuple(
            entry for entry in self.entries if not selected_keys or entry.source_key in selected_keys
        )

        for entry in selected_entries:
            self.store.upsert_policy(entry.policy)

        run_id = self.store.begin_run(scope, started_at=started_at)
        metrics: dict[str, object] = {
            "source_count": len(selected_entries),
            "blocked_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "observation_count": 0,
            "candidate_count": 0,
            "inserted_count": 0,
            "updated_count": 0,
            "duplicate_count": 0,
            "expired_count": 0,
            "ranked_count": 0,
            "static_request_count": 0,
            "browser_request_count": 0,
        }
        active_by_fingerprint: dict[str, Discovery] = {}
        requests: list[AcquisitionRequest] = []
        entry_by_request: dict[tuple[str, str], SourceCatalogEntry] = {}

        for entry in selected_entries:
            if not entry.start_urls:
                metrics["skipped_count"] = int(metrics["skipped_count"]) + 1
                self.store.record_source_result(
                    run_id,
                    SourceRunResult(
                        source_key=entry.source_key,
                        status="skipped",
                        fetch_mode=entry.fetch_mode.value,
                        error_code="no_start_url",
                    ),
                )
                continue

            if entry.fetch_mode not in (FetchMode.STATIC, FetchMode.BROWSER):
                metrics["skipped_count"] = int(metrics["skipped_count"]) + 1
                self.store.record_source_result(
                    run_id,
                    SourceRunResult(
                        source_key=entry.source_key,
                        status="skipped",
                        fetch_mode=entry.fetch_mode.value,
                        error_code="non_web_acquisition_mode",
                    ),
                )
                continue

            for url in entry.start_urls:
                decision = self.policy_registry.decide(
                    entry.source_key,
                    scope=scope,
                    source_url=url,
                )
                if not decision.allowed or decision.mode is not SourceAccessMode.ALLOW:
                    metrics["blocked_count"] = int(metrics["blocked_count"]) + 1
                    self.store.record_source_result(
                        run_id,
                        SourceRunResult(
                            source_key=entry.source_key,
                            source_url=url,
                            fetch_mode=entry.fetch_mode.value,
                            status="blocked",
                            error_code="policy_denied",
                            detail=decision.reason,
                        ),
                    )
                    continue

                previous_requests = self.store.request_count_last_hour(entry.source_key, now=started_at)
                queued_for_source = sum(1 for item in requests if item.source_key == entry.source_key)
                if previous_requests + queued_for_source >= entry.policy.max_requests_per_hour:
                    metrics["blocked_count"] = int(metrics["blocked_count"]) + 1
                    self.store.record_source_result(
                        run_id,
                        SourceRunResult(
                            source_key=entry.source_key,
                            source_url=url,
                            fetch_mode=entry.fetch_mode.value,
                            status="blocked",
                            error_code="source_rate_cap",
                            detail=f"max_requests_per_hour={entry.policy.max_requests_per_hour}",
                        ),
                    )
                    continue

                request = AcquisitionRequest(
                    source_key=entry.source_key,
                    url=url,
                    fetch_mode=entry.fetch_mode,
                )
                requests.append(request)
                entry_by_request[(entry.source_key, url)] = entry
                metric_key = (
                    "browser_request_count"
                    if entry.fetch_mode is FetchMode.BROWSER
                    else "static_request_count"
                )
                metrics[metric_key] = int(metrics[metric_key]) + 1

        try:
            outcomes = tuple(self.acquisition.acquire(requests))
        except Exception as exc:
            metrics["failed_count"] = int(metrics["failed_count"]) + len(requests)
            for request in requests:
                self.store.record_source_result(
                    run_id,
                    SourceRunResult(
                        source_key=request.source_key,
                        source_url=request.url,
                        fetch_mode=request.fetch_mode.value,
                        status="error",
                        error_code="acquisition_backend_failure",
                        detail=type(exc).__name__,
                    ),
                )
            self.store.finalize_run(
                run_id,
                completed_at=datetime.now(timezone.utc),
                status="failed",
                metrics=metrics,
            )
            raise

        for outcome in outcomes:
            entry = entry_by_request.get((outcome.request.source_key, outcome.request.url))
            if entry is None:
                metrics["failed_count"] = int(metrics["failed_count"]) + 1
                continue
            if not outcome.ok or outcome.page is None:
                metrics["failed_count"] = int(metrics["failed_count"]) + 1
                self.store.record_source_result(
                    run_id,
                    SourceRunResult(
                        source_key=entry.source_key,
                        source_url=outcome.request.url,
                        fetch_mode=entry.fetch_mode.value,
                        status="error",
                        error_code=outcome.error_code or "unknown_acquisition_error",
                        detail=outcome.detail,
                    ),
                )
                continue

            page = outcome.page
            adapter = _adapter_for(entry, page.final_url)
            normalized = adapter.extract(
                source_key=entry.source_key,
                source_url=page.final_url,
                html=page.html,
                observed_at=page.observed_at,
                content_hash=page.content_hash,
            )
            observation = replace(
                normalized.observation,
                source_url=page.final_url,
                http_status=page.http_status,
            )
            quality_discoveries = tuple(
                item for item in normalized.discoveries if _is_poc_quality_candidate(item)
            )
            discoveries = tuple(
                _with_freshness(item, now=max(started_at, page.observed_at))
                for item in quality_discoveries
            )
            delta = self.store.persist_normalized(
                run_id=run_id,
                policy=entry.policy,
                observation=observation,
                discoveries=discoveries,
            )
            _add_delta(metrics, delta, candidate_count=len(discoveries))

            if len(discoveries) < entry.minimum_candidates:
                metrics["failed_count"] = int(metrics["failed_count"]) + 1
                self.store.record_source_result(
                    run_id,
                    SourceRunResult(
                        source_key=entry.source_key,
                        source_url=page.final_url,
                        fetch_mode=entry.fetch_mode.value,
                        status="error",
                        observed_at=page.observed_at,
                        http_status=page.http_status,
                        candidate_count=len(discoveries),
                        inserted_count=delta.inserted_count,
                        updated_count=delta.updated_count,
                        duplicate_count=delta.duplicate_count,
                        expired_count=delta.expired_count,
                        error_code="insufficient_candidates",
                        detail=f"minimum_candidates={entry.minimum_candidates}",
                    ),
                )
                continue

            for discovery in discoveries:
                fingerprint = discovery_fingerprint(discovery)
                existing = active_by_fingerprint.get(fingerprint)
                if existing is None or discovery.observed_at >= existing.observed_at:
                    active_by_fingerprint[fingerprint] = discovery

            self.store.record_source_result(
                run_id,
                SourceRunResult(
                    source_key=entry.source_key,
                    source_url=page.final_url,
                    fetch_mode=entry.fetch_mode.value,
                    status="ok",
                    observed_at=page.observed_at,
                    http_status=page.http_status,
                    candidate_count=len(discoveries),
                    inserted_count=delta.inserted_count,
                    updated_count=delta.updated_count,
                    duplicate_count=delta.duplicate_count,
                    expired_count=delta.expired_count,
                ),
            )

        rank_input = tuple(
            item for item in active_by_fingerprint.values() if item.freshness is not FreshnessState.EXPIRED
        )
        context = dict(rank_context or {})
        context.setdefault("now", datetime.now(timezone.utc))
        ranked = tuple(self.ranker.rank(rank_input, context=context))
        metrics["ranked_count"] = len(ranked)
        candidate_count = int(metrics["candidate_count"])
        metrics["duplicate_rate"] = (
            int(metrics["duplicate_count"]) / candidate_count if candidate_count else 0.0
        )
        metrics["expired_rate"] = (
            int(metrics["expired_count"]) / candidate_count if candidate_count else 0.0
        )

        failed_count = int(metrics["failed_count"])
        observation_count = int(metrics["observation_count"])
        status = "completed" if failed_count == 0 else ("partial" if observation_count else "failed")
        self.store.finalize_run(
            run_id,
            completed_at=datetime.now(timezone.utc),
            status=status,
            metrics=metrics,
        )
        return IngestionRunSummary(
            run_id=run_id,
            status=status,
            metrics=dict(metrics),
            ranked=ranked,
        )


def _adapter_for(entry: SourceCatalogEntry, source_url: str) -> SourceAdapter:
    adapter_kind = entry.adapter_kind_for(source_url)
    if adapter_kind is AdapterKind.STRUCTURED:
        return StructuredHtmlAdapter()
    if adapter_kind is AdapterKind.EVENT:
        return PublicWebSignalAdapter(TextSignalConfig(event_mode=True))
    if adapter_kind is AdapterKind.PROMOTION:
        return PublicWebSignalAdapter(TextSignalConfig(event_mode=False))
    raise ValueError(f"Adapter kind {adapter_kind.value} is not supported by web POC ingestion")


def _is_poc_quality_candidate(discovery: Discovery) -> bool:
    # Esplora's promotion T&C page contains spend thresholds and entitlement counts.
    # They are not old/current sale prices; preserving them as price deltas creates false deals.
    if (
        discovery.source_key == "esplora_family_promotions"
        and discovery.discovery_type is DiscoveryType.DEAL
        and (discovery.original_price is not None or discovery.current_price is not None)
    ):
        return False
    return True


def _with_freshness(discovery: Discovery, *, now: datetime) -> Discovery:
    freshness = classify_freshness(
        FreshnessInput(
            observed_at=discovery.observed_at,
            now=now,
            starts_at=discovery.starts_at,
            expires_at=discovery.expires_at,
            is_event=discovery.discovery_type is DiscoveryType.EVENT,
        )
    )
    return replace(discovery, freshness=freshness)


def _add_delta(metrics: dict[str, object], delta: PersistenceDelta, *, candidate_count: int) -> None:
    metrics["observation_count"] = int(metrics["observation_count"]) + delta.observation_count
    metrics["candidate_count"] = int(metrics["candidate_count"]) + candidate_count
    metrics["inserted_count"] = int(metrics["inserted_count"]) + delta.inserted_count
    metrics["updated_count"] = int(metrics["updated_count"]) + delta.updated_count
    metrics["duplicate_count"] = int(metrics["duplicate_count"]) + delta.duplicate_count
    metrics["expired_count"] = int(metrics["expired_count"]) + delta.expired_count


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
