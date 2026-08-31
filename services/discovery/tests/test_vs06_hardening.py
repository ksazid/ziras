from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from ziras_discovery.acquisition import AcquiredPage, AcquisitionOutcome, AcquisitionRequest
from ziras_discovery.adapters.public_web import PublicWebSignalAdapter, TextSignalConfig
from ziras_discovery.domain import SourceAccessMode, SourcePolicy, SourcePolicyScope
from ziras_discovery.persistence import PersistenceDelta, SourceRunResult
from ziras_discovery.pipeline import PocIngestionPipeline
from ziras_discovery.policy import SourcePolicyRegistry
from ziras_discovery.ranking import DeterministicRanker
from ziras_discovery.source_catalog import AdapterKind, FetchMode, SourceCatalogEntry


NOW = datetime(2026, 8, 31, 13, 0, tzinfo=timezone.utc)


class FakeAcquisition:
    def __init__(self, html_by_url: dict[str, str]) -> None:
        self.html_by_url = html_by_url
        self.requests: tuple[AcquisitionRequest, ...] = ()

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
                    html=self.html_by_url[request.url],
                    observed_at=NOW,
                    content_hash=f"hash-{index}",
                    http_status=200,
                ),
            )
            for index, request in enumerate(self.requests)
        )


class FakeStore:
    def __init__(self) -> None:
        self.run_id = UUID("00000000-0000-0000-0000-000000000006")
        self.results: list[SourceRunResult] = []
        self.persisted = []
        self.final = None

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
        self.final = {"status": status, **dict(metrics)}


def _policy(source_key: str, paths: tuple[str, ...]) -> SourcePolicy:
    return SourcePolicy(
        source_key=source_key,
        mode=SourceAccessMode.ALLOW,
        reason="fixture",
        scope=SourcePolicyScope.POC,
        allowed_path_prefixes=paths,
        max_requests_per_hour=max(1, len(paths)),
    )


def _event_html() -> str:
    return """
    <html><head><script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Event",
      "name": "Cinema Premiere Night",
      "startDate": "2026-09-02T19:00:00+02:00",
      "endDate": "2026-09-02T22:00:00+02:00"
    }
    </script></head><body>Cinema Premiere Night</body></html>
    """


def _deal_html() -> str:
    return """
    <html><head><script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Product",
      "name": "Cinema Combo",
      "offers": {
        "@type": "Offer",
        "price": "9.90",
        "priceCurrency": "EUR",
        "priceValidUntil": "2026-09-03"
      }
    }
    </script></head><body>Cinema Combo</body></html>
    """


def test_route_adapter_kind_uses_longest_matching_path_prefix() -> None:
    entry = SourceCatalogEntry(
        source_key="eden",
        display_name="Eden",
        source_class="entertainment",
        start_urls=("https://example.com/special-offers", "https://example.com/whats-on"),
        fetch_mode=FetchMode.STATIC,
        adapter_kind=AdapterKind.STRUCTURED,
        policy=_policy("eden", ("/special-offers", "/whats-on")),
        route_adapter_kinds=(
            ("/", AdapterKind.STRUCTURED),
            ("/special-offers", AdapterKind.PROMOTION),
            ("/whats-on", AdapterKind.EVENT),
        ),
    )

    assert entry.adapter_kind_for("https://example.com/special-offers") is AdapterKind.PROMOTION
    assert entry.adapter_kind_for("https://example.com/whats-on") is AdapterKind.EVENT


def test_eden_mixed_routes_keep_promotion_and_event_semantics_separate() -> None:
    offers_url = "https://example.com/special-offers"
    events_url = "https://example.com/whats-on"
    entry = SourceCatalogEntry(
        source_key="eden",
        display_name="Eden",
        source_class="entertainment",
        start_urls=(offers_url, events_url),
        fetch_mode=FetchMode.STATIC,
        adapter_kind=AdapterKind.PROMOTION,
        policy=_policy("eden", ("/special-offers", "/whats-on")),
        route_adapter_kinds=(("/whats-on", AdapterKind.EVENT),),
    )
    acquisition = FakeAcquisition({offers_url: _deal_html(), events_url: _event_html()})
    store = FakeStore()
    pipeline = PocIngestionPipeline(
        entries=(entry,),
        policy_registry=SourcePolicyRegistry({entry.source_key: entry.policy}),
        acquisition=acquisition,
        store=store,
        ranker=DeterministicRanker(),
    )

    summary = pipeline.run(scope=SourcePolicyScope.POC, now=NOW)

    assert summary.status == "completed"
    by_title = {item.title: item.discovery_type.value for item in store.persisted}
    assert by_title == {"Cinema Combo": "deal", "Cinema Premiere Night": "event"}


def test_browser_source_with_empty_rendered_inventory_fails_health_check() -> None:
    url = "https://example.com/events"
    entry = SourceCatalogEntry(
        source_key="browser-events",
        display_name="Browser events",
        source_class="events",
        start_urls=(url,),
        fetch_mode=FetchMode.BROWSER,
        adapter_kind=AdapterKind.EVENT,
        policy=_policy("browser-events", ("/events",)),
        minimum_candidates=1,
    )
    acquisition = FakeAcquisition({url: "<html><body><div id='app'>Browse Events</div></body></html>"})
    store = FakeStore()
    pipeline = PocIngestionPipeline(
        entries=(entry,),
        policy_registry=SourcePolicyRegistry({entry.source_key: entry.policy}),
        acquisition=acquisition,
        store=store,
        ranker=DeterministicRanker(),
    )

    summary = pipeline.run(scope=SourcePolicyScope.POC, now=NOW)

    assert acquisition.requests[0].fetch_mode is FetchMode.BROWSER
    assert summary.status == "partial"
    assert summary.ranked == ()
    assert store.results[-1].status == "error"
    assert store.results[-1].error_code == "insufficient_candidates"


def test_browser_source_with_rendered_event_passes_health_check() -> None:
    url = "https://example.com/events"
    entry = SourceCatalogEntry(
        source_key="browser-events",
        display_name="Browser events",
        source_class="events",
        start_urls=(url,),
        fetch_mode=FetchMode.BROWSER,
        adapter_kind=AdapterKind.EVENT,
        policy=_policy("browser-events", ("/events",)),
        minimum_candidates=1,
    )
    acquisition = FakeAcquisition({url: _event_html()})
    store = FakeStore()
    pipeline = PocIngestionPipeline(
        entries=(entry,),
        policy_registry=SourcePolicyRegistry({entry.source_key: entry.policy}),
        acquisition=acquisition,
        store=store,
        ranker=DeterministicRanker(),
    )

    summary = pipeline.run(scope=SourcePolicyScope.POC, now=NOW)

    assert summary.status == "completed"
    assert summary.metrics["browser_request_count"] == 1
    assert len(summary.ranked) == 1
    assert summary.ranked[0].discovery_type.value == "event"


def test_visitmalta_numeric_date_range_uses_following_event_title() -> None:
    adapter = PublicWebSignalAdapter(TextSignalConfig(event_mode=True))
    result = adapter.extract(
        source_key="visitmalta_events",
        source_url="https://www.visitmalta.com/en/events-in-malta-and-gozo/",
        html="""
        <html><body>
          <div>03/09/2026 - 06/09/2026</div>
          <h3>Breaking Borders</h3>
          <p>World's Biggest Desi destination festival</p>
        </body></html>
        """,
        observed_at=NOW,
    )

    assert len(result.discoveries) == 1
    assert result.discoveries[0].title == "Breaking Borders"
    assert result.discoveries[0].starts_at == datetime(2026, 9, 3, tzinfo=timezone.utc)
    assert result.discoveries[0].expires_at == datetime(2026, 9, 6, 23, 59, 59, tzinfo=timezone.utc)


def test_sale_listing_accepts_current_price_before_original_price() -> None:
    adapter = PublicWebSignalAdapter(TextSignalConfig(event_mode=False))
    result = adapter.extract(
        source_key="eurosport_malta_sale",
        source_url="https://www.eurosport.com.mt/sale",
        html="""
        <html><body>
          <h3>Treadmove Running Shoes</h3>
          <div>€25.00 €50.00</div>
        </body></html>
        """,
        observed_at=NOW,
    )

    assert len(result.discoveries) == 1
    assert result.discoveries[0].title == "Treadmove Running Shoes"
    assert result.discoveries[0].current_price == Decimal("25.00")
    assert result.discoveries[0].original_price == Decimal("50.00")


def test_special_offers_can_emit_qualitative_offer_titles_without_fake_prices() -> None:
    adapter = PublicWebSignalAdapter(TextSignalConfig(event_mode=False))
    result = adapter.extract(
        source_key="eden_cinemas",
        source_url="https://www.edencinemas.com.mt/special-offers",
        html="""
        <html><body>
          <h1>SPECIAL OFFERS</h1>
          <h2>FAMILY DEAL</h2>
          <p>Family cinema package.</p>
          <h2>YOUTH OFFER</h2>
          <p>Weekday offer for younger moviegoers.</p>
        </body></html>
        """,
        observed_at=NOW,
    )

    assert {item.title for item in result.discoveries} == {"FAMILY DEAL", "YOUTH OFFER"}
    assert all(item.current_price is None for item in result.discoveries)


def test_whats_on_listing_can_emit_current_ticketed_titles_without_dates() -> None:
    adapter = PublicWebSignalAdapter(TextSignalConfig(event_mode=True))
    result = adapter.extract(
        source_key="eden_cinemas",
        source_url="https://www.edencinemas.com.mt/whats-on",
        html="""
        <html><body>
          <h1>WHAT’S ON</h1>
          <div><a href='/movie/moana'>Moana</a> <a href='/movie/moana'>Buy Tickets</a></div>
          <div><a href='/movie/odyssey'>The Odyssey</a> <a href='/movie/odyssey'>Buy Tickets</a></div>
        </body></html>
        """,
        observed_at=NOW,
    )

    assert {item.title for item in result.discoveries} == {"Moana", "The Odyssey"}
