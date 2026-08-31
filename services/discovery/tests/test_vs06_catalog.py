from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from ziras_discovery.acquisition import AcquiredPage, AcquisitionOutcome
from ziras_discovery.domain import SourceAccessMode, SourcePolicyScope
from ziras_discovery.persistence import PersistenceDelta, SourceRunResult
from ziras_discovery.pipeline import PocIngestionPipeline
from ziras_discovery.policy import SourcePolicyRegistry
from ziras_discovery.ranking import DeterministicRanker
from ziras_discovery.source_catalog import (
    AdapterKind,
    FetchMode,
    default_malta_poc_extension_path,
    load_source_catalog,
)


NOW = datetime(2026, 8, 31, 13, 30, tzinfo=timezone.utc)


class VisitMaltaFixtureAcquisition:
    def __init__(self, html: str) -> None:
        self.html = html
        self.requests = ()

    def acquire(self, requests):
        self.requests = tuple(requests)
        return tuple(
            AcquisitionOutcome(
                request=request,
                page=AcquiredPage(
                    source_key=request.source_key,
                    requested_url=request.url,
                    final_url=request.url,
                    fetch_mode=request.fetch_mode,
                    html=self.html,
                    observed_at=NOW,
                    content_hash="visitmalta-rendered-fixture",
                    http_status=200,
                ),
            )
            for request in self.requests
        )


class FixtureStore:
    def __init__(self) -> None:
        self.run_id = UUID("00000000-0000-0000-0000-000000000606")
        self.results: list[SourceRunResult] = []
        self.persisted = []

    def upsert_policy(self, policy):
        return None

    def begin_run(self, scope, *, started_at):
        return self.run_id

    def request_count_last_hour(self, source_key, *, now):
        return 0

    def persist_normalized(self, *, run_id, policy, observation, discoveries):
        self.persisted.extend(discoveries)
        return PersistenceDelta(observation_count=1, inserted_count=len(discoveries))

    def record_source_result(self, run_id, result):
        self.results.append(result)

    def finalize_run(self, run_id, *, completed_at, status, metrics):
        return None


def test_vs06_extension_contains_exact_five_certified_poc_source_classes() -> None:
    entries = load_source_catalog(extension_path=default_malta_poc_extension_path())
    by_key = {entry.source_key: entry for entry in entries}

    poc = [
        entry
        for entry in entries
        if entry.policy.mode is SourceAccessMode.ALLOW
        and entry.policy.scope is SourcePolicyScope.POC
    ]
    classes = {entry.source_class for entry in poc}

    assert classes == {
        "events-official",
        "entertainment-offers",
        "home-retail",
        "cultural-venue-events",
        "sports-retail",
    }
    assert by_key["spazju_kreattiv_events"].policy.scope is SourcePolicyScope.POC
    assert by_key["spazju_kreattiv_events"].policy.max_requests_per_hour == 1
    assert by_key["eurosport_malta_sale"].policy.scope is SourcePolicyScope.POC
    assert by_key["eurosport_malta_sale"].policy.max_requests_per_hour == 1
    assert by_key["spazju_kreattiv_events"].policy.content_storage_allowed is False
    assert by_key["eurosport_malta_sale"].policy.content_storage_allowed is False
    assert by_key["eden_cinemas"].adapter_kind is AdapterKind.PROMOTION
    assert by_key["visitmalta_events"].fetch_mode is FetchMode.BROWSER


def test_configured_visitmalta_browser_entry_accepts_rendered_event_fixture() -> None:
    entry = next(item for item in load_source_catalog() if item.source_key == "visitmalta_events")
    acquisition = VisitMaltaFixtureAcquisition(
        """
        <html><head><script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Event",
          "name": "Valletta September Festival",
          "startDate": "2026-09-12T18:00:00+02:00",
          "endDate": "2026-09-12T23:00:00+02:00"
        }
        </script></head><body><div id="app">Valletta September Festival</div></body></html>
        """
    )
    store = FixtureStore()
    pipeline = PocIngestionPipeline(
        entries=(entry,),
        policy_registry=SourcePolicyRegistry({entry.source_key: entry.policy}),
        acquisition=acquisition,
        store=store,
        ranker=DeterministicRanker(),
    )

    summary = pipeline.run(scope=SourcePolicyScope.POC, now=NOW)

    assert summary.status == "completed"
    assert len(acquisition.requests) == 1
    assert acquisition.requests[0].fetch_mode is FetchMode.BROWSER
    assert summary.metrics["browser_request_count"] == 1
    assert summary.metrics["candidate_count"] == 1
    assert len(summary.ranked) == 1
    assert summary.ranked[0].title == "Valletta September Festival"
    assert store.results[-1].status == "ok"


def test_existing_restricted_sources_are_not_relaxed_by_vs06() -> None:
    by_key = {entry.source_key: entry for entry in load_source_catalog()}

    assert by_key["mcdonalds_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["pizzahut_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["franks_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["wolt_malta"].policy.mode is SourceAccessMode.PARTNER_ONLY
    assert by_key["zara_malta"].policy.mode is SourceAccessMode.PARTNER_ONLY
    assert by_key["cloudigo_malta"].policy.mode is SourceAccessMode.PARTNER_ONLY
    assert by_key["lidl_malta_offers"].policy.scope is SourcePolicyScope.RESEARCH
    assert by_key["eurospin_promotions"].policy.scope is SourcePolicyScope.RESEARCH


def test_custom_catalog_does_not_implicitly_apply_default_extension_or_hardening(tmp_path: Path) -> None:
    custom = tmp_path / "catalog.json"
    custom.write_text("[]", encoding="utf-8")

    assert load_source_catalog(custom) == ()


def test_extension_duplicate_source_is_rejected(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    extension = tmp_path / "extension.json"
    payload = """[
      {
        "source_key": "fixture",
        "display_name": "Fixture",
        "source_class": "fixture",
        "start_urls": ["https://example.com/offers"],
        "fetch_mode": "static",
        "adapter_kind": "promotion",
        "policy": {
          "mode": "allow",
          "scope": "poc",
          "reason": "fixture",
          "allowed_path_prefixes": ["/offers"]
        }
      }
    ]"""
    catalog.write_text(payload, encoding="utf-8")
    extension.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate source_key"):
        load_source_catalog(catalog, extension_path=extension)


def test_hardening_overlay_cannot_change_policy_authority(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        """[
          {
            "source_key": "fixture",
            "display_name": "Fixture",
            "source_class": "fixture",
            "start_urls": ["https://example.com/offers"],
            "fetch_mode": "static",
            "adapter_kind": "promotion",
            "policy": {
              "mode": "allow",
              "scope": "poc",
              "reason": "fixture",
              "allowed_path_prefixes": ["/offers"]
            }
          }
        ]""",
        encoding="utf-8",
    )
    hardening = tmp_path / "hardening.json"
    hardening.write_text(
        '{"fixture": {"policy": {"mode": "deny"}}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot mutate policy/catalog authority"):
        load_source_catalog(catalog, hardening_path=hardening)
