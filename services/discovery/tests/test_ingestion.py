from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from ziras_discovery.acquisition import (
    AcquiredPage,
    AcquisitionOutcome,
    AcquisitionRequest,
)
from ziras_discovery.domain import (
    Discovery,
    DiscoveryType,
    FreshnessState,
    SourceAccessMode,
    SourcePolicy,
    SourcePolicyScope,
)
from ziras_discovery.persistence import PersistenceDelta, SourceRunResult, discovery_fingerprint
from ziras_discovery.pipeline import PocIngestionPipeline
from ziras_discovery.policy import SourcePolicyRegistry
from ziras_discovery.ranking import DeterministicRanker
from ziras_discovery.source_catalog import AdapterKind, FetchMode, SourceCatalogEntry


NOW = datetime(2026, 8, 31, 8, 0, tzinfo=timezone.utc)


class FakeAcquisition:
    def __init__(self, html_by_source: dict[str, str]) -> None:
        self.html_by_source = html_by_source
        self.requests: tuple[AcquisitionRequest, ...] = ()

    def acquire(self, requests):
        self.requests = tuple(requests)
        result = []
        for request in self.requests:
            html = self.html_by_source[request.source_key]
            result.append(
                AcquisitionOutcome(
                    request=request,
                    page=AcquiredPage(
                        source_key=request.source_key,
                        requested_url=request.url,
                        final_url=request.url,
                        fetch_mode=request.fetch_mode,
                        html=html,
                        observed_at=NOW,
                        content_hash=f"hash-{request.source_key}",
                        http_status=200,
                    ),
                )
            )
        return tuple(result)


class FakeStore:
    def __init__(self) -> None:
        self.run_id = UUID("00000000-0000-0000-0000-000000000005")
        self.results: list[SourceRunResult] = []
        self.final: dict[str, object] | None = None
        self.persisted: list[Discovery] = []

    def upsert_policy(self, policy):
        return None

    def begin_run(self, scope, *, started_at):
        return self.run_id

    def request_count_last_hour(self, source_key, *, now):
        return 0

    def persist_normalized(self, *, run_id, policy, observation, discoveries):
        self.persisted.extend(discoveries)
        return PersistenceDelta(
            observation_count=1,
            inserted_count=len(discoveries),
            expired_count=sum(1 for item in discoveries if item.freshness is FreshnessState.EXPIRED),
        )

    def record_source_result(self, run_id, result):
        self.results.append(result)

    def finalize_run(self, run_id, *, completed_at, status, metrics):
        self.final = {"status": status, **dict(metrics)}


def _entry(
    source_key: str,
    *,
    fetch_mode: FetchMode,
    adapter_kind: AdapterKind,
    policy_mode: SourceAccessMode = SourceAccessMode.ALLOW,
    policy_scope: SourcePolicyScope = SourcePolicyScope.POC,
) -> SourceCatalogEntry:
    url = f"https://{source_key}.example/offers"
    policy = SourcePolicy(
        source_key=source_key,
        mode=policy_mode,
        reason="fixture",
        scope=policy_scope,
        allowed_path_prefixes=("/offers",),
        max_requests_per_hour=1,
    )
    return SourceCatalogEntry(
        source_key=source_key,
        display_name=source_key,
        source_class="fixture",
        start_urls=(url,),
        fetch_mode=fetch_mode,
        adapter_kind=adapter_kind,
        policy=policy,
    )


def _product_html(*, valid_until: str = "2026-09-05") -> str:
    return f"""
    <html><head><script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "Product",
      "name": "Desk Lamp",
      "offers": {{
        "@type": "Offer",
        "price": "19.90",
        "priceCurrency": "EUR",
        "priceValidUntil": "{valid_until}"
      }}
    }}
    </script></head><body>Desk Lamp</body></html>
    """


def _event_html() -> str:
    return """
    <html><head><script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Event",
      "name": "Valletta Night Market",
      "startDate": "2026-09-01T18:00:00+02:00",
      "endDate": "2026-09-01T23:00:00+02:00"
    }
    </script></head><body>Valletta Night Market</body></html>
    """


def test_pipeline_routes_only_policy_allowed_web_sources_and_preserves_fetch_mode() -> None:
    static = _entry("static-source", fetch_mode=FetchMode.STATIC, adapter_kind=AdapterKind.PROMOTION)
    browser = _entry("browser-source", fetch_mode=FetchMode.BROWSER, adapter_kind=AdapterKind.EVENT)
    denied = _entry(
        "denied-source",
        fetch_mode=FetchMode.STATIC,
        adapter_kind=AdapterKind.PROMOTION,
        policy_mode=SourceAccessMode.DENY,
    )
    research_only = _entry(
        "research-source",
        fetch_mode=FetchMode.STATIC,
        adapter_kind=AdapterKind.PROMOTION,
        policy_scope=SourcePolicyScope.RESEARCH,
    )
    entries = (static, browser, denied, research_only)
    acquisition = FakeAcquisition(
        {
            "static-source": _product_html(),
            "browser-source": _event_html(),
        }
    )
    store = FakeStore()
    pipeline = PocIngestionPipeline(
        entries=entries,
        policy_registry=SourcePolicyRegistry({item.source_key: item.policy for item in entries}),
        acquisition=acquisition,
        store=store,
        ranker=DeterministicRanker(),
    )

    summary = pipeline.run(scope=SourcePolicyScope.POC, now=NOW)

    assert {(item.source_key, item.fetch_mode) for item in acquisition.requests} == {
        ("static-source", FetchMode.STATIC),
        ("browser-source", FetchMode.BROWSER),
    }
    assert summary.status == "completed"
    assert summary.metrics["blocked_count"] == 2
    assert summary.metrics["observation_count"] == 2
    assert summary.metrics["candidate_count"] == 2
    assert summary.metrics["ranked_count"] == 2
    assert {item.discovery_type for item in summary.ranked} == {DiscoveryType.DEAL, DiscoveryType.EVENT}


def test_explicitly_expired_candidate_is_persisted_but_not_ranked() -> None:
    entry = _entry("expired-source", fetch_mode=FetchMode.STATIC, adapter_kind=AdapterKind.PROMOTION)
    acquisition = FakeAcquisition({"expired-source": _product_html(valid_until="2026-08-30")})
    store = FakeStore()
    pipeline = PocIngestionPipeline(
        entries=(entry,),
        policy_registry=SourcePolicyRegistry({entry.source_key: entry.policy}),
        acquisition=acquisition,
        store=store,
        ranker=DeterministicRanker(),
    )

    summary = pipeline.run(scope=SourcePolicyScope.POC, now=NOW)

    assert len(store.persisted) == 1
    assert store.persisted[0].freshness is FreshnessState.EXPIRED
    assert summary.metrics["expired_count"] == 1
    assert summary.ranked == ()


def test_discovery_fingerprint_dedupes_equivalent_cross_source_records() -> None:
    first = Discovery(
        id=uuid4(),
        discovery_type=DiscoveryType.DEAL,
        entity_id=None,
        title="Desk Lamp",
        source_key="source-a",
        source_url="https://a.example/item",
        observed_at=NOW,
        current_price=Decimal("19.90"),
        currency="EUR",
        expires_at=NOW + timedelta(days=5),
        freshness=FreshnessState.LIKELY_LIVE,
    )
    second = replace(
        first,
        id=uuid4(),
        source_key="source-b",
        source_url="https://b.example/product/desk-lamp",
        observed_at=NOW + timedelta(minutes=3),
    )
    changed_price = replace(second, current_price=Decimal("18.90"))

    assert discovery_fingerprint(first) == discovery_fingerprint(second)
    assert discovery_fingerprint(first) != discovery_fingerprint(changed_price)


def test_deterministic_ranker_prefers_fresher_high_value_discovery_and_excludes_expired() -> None:
    base = Discovery(
        id=uuid4(),
        discovery_type=DiscoveryType.DEAL,
        entity_id=None,
        title="Basic offer",
        source_key="source",
        source_url="https://example.com",
        observed_at=NOW,
        current_price=Decimal("90"),
        original_price=Decimal("100"),
        currency="EUR",
        freshness=FreshnessState.UNVERIFIED,
    )
    better = replace(
        base,
        id=uuid4(),
        title="Fashion weekend sale",
        current_price=Decimal("50"),
        freshness=FreshnessState.VERIFIED_LIVE,
        expires_at=NOW + timedelta(hours=12),
    )
    expired = replace(
        base,
        id=uuid4(),
        title="Expired sale",
        freshness=FreshnessState.EXPIRED,
    )

    ranked = DeterministicRanker().rank(
        (base, expired, better),
        context={"now": NOW, "interest_terms": ("fashion",)},
    )

    assert tuple(item.id for item in ranked) == (better.id, base.id)
