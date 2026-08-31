from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import ipaddress
import socket
from typing import Protocol, Sequence
from urllib.parse import urlsplit

from .source_catalog import FetchMode


USER_AGENT = "Ziras-POC/0.2 (+https://github.com/ksazid/ziras)"


@dataclass(frozen=True, slots=True)
class AcquisitionRequest:
    source_key: str
    url: str
    fetch_mode: FetchMode


@dataclass(frozen=True, slots=True)
class AcquiredPage:
    source_key: str
    requested_url: str
    final_url: str
    fetch_mode: FetchMode
    html: str
    observed_at: datetime
    content_hash: str
    http_status: int


@dataclass(frozen=True, slots=True)
class AcquisitionOutcome:
    request: AcquisitionRequest
    page: AcquiredPage | None = None
    error_code: str | None = None
    detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.page is not None and self.error_code is None


class AcquisitionBackend(Protocol):
    def acquire(self, requests: Sequence[AcquisitionRequest]) -> Sequence[AcquisitionOutcome]: ...


class ScrapyPlaywrightAcquirer:
    """One-shot POC batch acquisition using Scrapy with Playwright only for browser entries.

    The caller must policy-check source/scope/path before constructing requests. Scrapy robots
    enforcement remains enabled. Redirect middleware is disabled; browser responses are also
    rejected if the final top-level host changes.
    """

    def __init__(
        self,
        *,
        timeout_seconds: int = 30,
        concurrent_requests: int = 2,
        browser_settle_ms: int = 2500,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.concurrent_requests = concurrent_requests
        self.browser_settle_ms = browser_settle_ms

    def acquire(self, requests: Sequence[AcquisitionRequest]) -> Sequence[AcquisitionOutcome]:
        if not requests:
            return ()

        try:
            import scrapy
            from scrapy.crawler import CrawlerProcess
            from scrapy_playwright.page import PageMethod
        except ImportError as exc:  # pragma: no cover - exercised only without optional deps
            raise RuntimeError(
                "POC acquisition dependencies are missing; install ziras-discovery[acquisition]."
            ) from exc

        safe_requests: list[AcquisitionRequest] = []
        outcomes: list[AcquisitionOutcome] = []
        for request in requests:
            try:
                _assert_public_host(request.url)
            except Exception as exc:
                outcomes.append(
                    AcquisitionOutcome(
                        request=request,
                        error_code="unsafe_destination",
                        detail=type(exc).__name__,
                    )
                )
                continue
            safe_requests.append(request)

        if not safe_requests:
            return tuple(outcomes)

        settings = {
            "ROBOTSTXT_OBEY": True,
            "USER_AGENT": USER_AGENT,
            "DOWNLOAD_TIMEOUT": self.timeout_seconds,
            "CONCURRENT_REQUESTS": self.concurrent_requests,
            "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
            "REDIRECT_ENABLED": False,
            "RETRY_ENABLED": False,
            "LOG_ENABLED": False,
            "TELNETCONSOLE_ENABLED": False,
            "DOWNLOAD_HANDLERS": {
                "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
                "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            },
            "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        }

        collected: list[AcquisitionOutcome] = []
        requested_by_token = {str(index): request for index, request in enumerate(safe_requests)}
        browser_settle_ms = self.browser_settle_ms

        class PocSpider(scrapy.Spider):
            name = "ziras_poc_ingestion"

            def _initial_requests(self):
                for token, request in requested_by_token.items():
                    meta = {
                        "ziras_token": token,
                        "handle_httpstatus_all": True,
                    }
                    if request.fetch_mode is FetchMode.BROWSER:
                        meta["playwright"] = True
                        meta["playwright_page_methods"] = [
                            PageMethod("wait_for_timeout", browser_settle_ms)
                        ]
                    yield scrapy.Request(
                        request.url,
                        headers={"Accept": "text/html,application/xhtml+xml"},
                        meta=meta,
                        callback=self.parse_page,
                        errback=self.parse_error,
                        dont_filter=True,
                    )

            async def start(self):
                for request in self._initial_requests():
                    yield request

            # Compatibility for Scrapy <2.13. Scrapy 2.18+ calls start().
            def start_requests(self):
                yield from self._initial_requests()

            def parse_page(self, response):
                token = response.meta["ziras_token"]
                request = requested_by_token[token]
                final_url = str(response.url)
                if _host(final_url) != _host(request.url):
                    collected.append(
                        AcquisitionOutcome(
                            request=request,
                            error_code="cross_host_redirect",
                            detail=final_url,
                        )
                    )
                    return
                status = int(response.status)
                if status < 200 or status >= 300:
                    collected.append(
                        AcquisitionOutcome(
                            request=request,
                            error_code=f"http_{status}",
                            detail="non_success_response",
                        )
                    )
                    return
                body = bytes(response.body)
                collected.append(
                    AcquisitionOutcome(
                        request=request,
                        page=AcquiredPage(
                            source_key=request.source_key,
                            requested_url=request.url,
                            final_url=final_url,
                            fetch_mode=request.fetch_mode,
                            html=body.decode("utf-8", errors="replace"),
                            observed_at=datetime.now(timezone.utc),
                            content_hash=sha256(body).hexdigest(),
                            http_status=status,
                        ),
                    )
                )

            def parse_error(self, failure):
                request_obj = failure.request
                token = request_obj.meta["ziras_token"]
                request = requested_by_token[token]
                collected.append(
                    AcquisitionOutcome(
                        request=request,
                        error_code="acquisition_error",
                        detail=type(failure.value).__name__,
                    )
                )

        process = CrawlerProcess(settings=settings)
        process.crawl(PocSpider)
        process.start(stop_after_crawl=True, install_signal_handlers=False)
        outcomes.extend(collected)

        completed = {(item.request.source_key, item.request.url) for item in outcomes}
        for request in safe_requests:
            if (request.source_key, request.url) not in completed:
                outcomes.append(
                    AcquisitionOutcome(
                        request=request,
                        error_code="missing_outcome",
                        detail="crawler_completed_without_result",
                    )
                )
        return tuple(outcomes)


def _assert_public_host(url: str) -> None:
    host = _host(url)
    if not host:
        raise ValueError("URL has no host")
    for item in socket.getaddrinfo(host, None):
        address = ipaddress.ip_address(item[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            raise RuntimeError("non-public destination rejected")


def _host(url: str) -> str | None:
    host = urlsplit(url).hostname
    return host.casefold() if host else None
