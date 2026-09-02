from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import sys
from types import ModuleType

from ziras_discovery import acquisition as acquisition_module
from ziras_discovery.acquisition import AcquisitionRequest, ScrapyPlaywrightAcquirer
from ziras_discovery.adapters.public_web import PublicWebSignalAdapter, TextSignalConfig
from ziras_discovery.source_catalog import FetchMode


NOW = datetime(2026, 8, 31, 18, 0, tzinfo=timezone.utc)


def test_scrapy_218_start_schedules_static_and_browser_requests(monkeypatch) -> None:
    scheduled = []
    crawler_settings = []

    class FakeSpider:
        pass

    class FakeRequest:
        def __init__(
            self,
            url,
            *,
            headers,
            meta,
            callback,
            errback,
            dont_filter,
        ) -> None:
            self.url = url
            self.headers = headers
            self.meta = meta
            self.callback = callback
            self.errback = errback
            self.dont_filter = dont_filter

    class FakePageMethod:
        def __init__(self, method, *args, **kwargs) -> None:
            self.method = method
            self.args = args
            self.kwargs = kwargs

    class FakeResponse:
        def __init__(self, request: FakeRequest) -> None:
            self.meta = request.meta
            self.url = request.url
            self.status = 200
            self.body = b"<html><body>POC fixture</body></html>"

    class FakeCrawlerProcess:
        def __init__(self, *, settings) -> None:
            self.settings = settings
            crawler_settings.append(settings)
            self.spider_cls = None

        def crawl(self, spider_cls) -> None:
            self.spider_cls = spider_cls

        def start(self, *, stop_after_crawl, install_signal_handlers) -> None:
            assert self.spider_cls is not None
            spider = self.spider_cls()

            async def run_start() -> None:
                async for request in spider.start():
                    scheduled.append(request)
                    request.callback(FakeResponse(request))

            asyncio.run(run_start())

    scrapy_module = ModuleType("scrapy")
    scrapy_module.Spider = FakeSpider
    scrapy_module.Request = FakeRequest
    crawler_module = ModuleType("scrapy.crawler")
    crawler_module.CrawlerProcess = FakeCrawlerProcess
    playwright_module = ModuleType("scrapy_playwright")
    playwright_page_module = ModuleType("scrapy_playwright.page")
    playwright_page_module.PageMethod = FakePageMethod

    monkeypatch.setitem(sys.modules, "scrapy", scrapy_module)
    monkeypatch.setitem(sys.modules, "scrapy.crawler", crawler_module)
    monkeypatch.setitem(sys.modules, "scrapy_playwright", playwright_module)
    monkeypatch.setitem(sys.modules, "scrapy_playwright.page", playwright_page_module)
    monkeypatch.setattr(acquisition_module, "_assert_public_host", lambda url: None)

    requests = (
        AcquisitionRequest("static", "https://static.example/offers", FetchMode.STATIC),
        AcquisitionRequest("browser", "https://browser.example/events", FetchMode.BROWSER),
    )

    outcomes = ScrapyPlaywrightAcquirer(
        timeout_seconds=60,
        browser_settle_ms=2500,
    ).acquire(requests)

    assert len(scheduled) == 2
    assert scheduled[0].meta.get("playwright") is None
    assert scheduled[1].meta["playwright"] is True
    page_method = scheduled[1].meta["playwright_page_methods"][0]
    assert page_method.method == "wait_for_timeout"
    assert page_method.args == (2500,)
    assert crawler_settings[0]["DOWNLOAD_TIMEOUT"] == 60
    assert crawler_settings[0]["PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT"] == 60000
    assert crawler_settings[0]["RETRY_ENABLED"] is False
    assert all(outcome.ok for outcome in outcomes)
    assert [outcome.request for outcome in outcomes] == list(requests)


def test_promotion_adapter_accepts_sale_price_before_original_price() -> None:
    result = PublicWebSignalAdapter(TextSignalConfig(event_mode=False)).extract(
        source_key="sports-sale",
        source_url="https://example.com/sale",
        html="""
        <html><body>
          <div>Adidas Performance</div>
          <h2>Predator League Boots</h2>
          <div>€70.00 €100.00</div>
        </body></html>
        """,
        observed_at=NOW,
    )

    discovery = next(item for item in result.discoveries if item.title == "Predator League Boots")
    assert str(discovery.current_price) == "70.00"
    assert str(discovery.original_price) == "100.00"


def test_promotion_adapter_keeps_named_offer_without_numeric_discount() -> None:
    result = PublicWebSignalAdapter(TextSignalConfig(event_mode=False)).extract(
        source_key="cinema-offers",
        source_url="https://example.com/special-offers",
        html="""
        <html><body>
          <h2>FAMILY DEAL</h2>
          <p>Includes cinema tickets, popcorn and drinks for families.</p>
        </body></html>
        """,
        observed_at=NOW,
    )

    assert any(item.title == "FAMILY DEAL" for item in result.discoveries)


def test_promotion_adapter_rejects_policy_heading_false_positive() -> None:
    result = PublicWebSignalAdapter(TextSignalConfig(event_mode=False)).extract(
        source_key="sports-sale",
        source_url="https://example.com/sale",
        html="<html><body><h2>Online Offers Terms & Conditions</h2></body></html>",
        observed_at=NOW,
    )

    assert result.discoveries == ()


def test_event_adapter_recovers_undated_buy_ticket_listing() -> None:
    result = PublicWebSignalAdapter(TextSignalConfig(event_mode=True)).extract(
        source_key="cinema-events",
        source_url="https://example.com/whats-on",
        html="""
        <html><body>
          <a href="/movie/moana">Moana</a>
          <a href="/movie/moana">Buy Tickets</a>
        </body></html>
        """,
        observed_at=NOW,
    )

    discovery = next(item for item in result.discoveries if item.title == "Moana")
    assert discovery.discovery_type.value == "event"
    assert discovery.source_url == "https://example.com/movie/moana"


def test_event_adapter_recovers_ticket_text_when_links_are_not_grouped() -> None:
    result = PublicWebSignalAdapter(TextSignalConfig(event_mode=True)).extract(
        source_key="cinema-events",
        source_url="https://example.com/whats-on",
        html="""
        <html><body>
          <h3>Moana</h3>
          <button>Buy Tickets</button>
        </body></html>
        """,
        observed_at=NOW,
    )

    assert any(item.title == "Moana" for item in result.discoveries)


def test_event_adapter_keeps_event_detail_link_but_rejects_language_listing_link() -> None:
    result = PublicWebSignalAdapter(TextSignalConfig(event_mode=True)).extract(
        source_key="visitmalta-events",
        source_url="https://www.visitmalta.com/en/events-in-malta-and-gozo/",
        html="""
        <html><body>
          <a href="/en/events-in-malta-and-gozo/event/malta-pride-march">Malta Pride March</a>
          <a href="/de/events-in-malta-and-gozo/">Deutsch</a>
          <a href="#jupiterx-main">Skip to content</a>
        </body></html>
        """,
        observed_at=NOW,
    )

    titles = {item.title for item in result.discoveries}
    assert "Malta Pride March" in titles
    assert "Deutsch" not in titles
    assert "Skip to content" not in titles
