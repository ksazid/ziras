from __future__ import annotations

import asyncio

from crawlee import ConcurrencySettings
from crawlee.crawlers import ParselCrawler, PlaywrightCrawler

from common import load_sources, robots_allowed, signals, write_results


async def fetch_parsel(source: dict) -> dict:
    row = {"id": source["id"], "class": source["class"], "adapter": "crawlee-parsel"}
    allowed, robots = robots_allowed(source["url"])
    row["robots"] = robots
    if not allowed:
        row["status"] = "SKIP_ROBOTS"
        return row
    captured = {"text": None}
    crawler = ParselCrawler(
        max_requests_per_crawl=1,
        max_request_retries=0,
        respect_robots_txt_file=True,
        concurrency_settings=ConcurrencySettings(max_concurrency=1, desired_concurrency=1),
    )

    @crawler.router.default_handler
    async def handler(context):
        captured["text"] = " ".join(context.selector.xpath("//body//text()").getall())

    try:
        await crawler.run([source["url"]])
        if captured["text"] is None:
            row["status"] = "NO_CONTENT"
        else:
            row.update(signals(captured["text"], source["expected"]))
            row["status"] = "PASS" if row["expected_ratio"] >= 0.5 else "WEAK"
    except Exception as exc:
        row.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
    return row


async def fetch_browser(source: dict) -> dict:
    row = {"id": source["id"], "class": source["class"], "adapter": "crawlee-playwright"}
    allowed, robots = robots_allowed(source["url"])
    row["robots"] = robots
    if not allowed:
        row["status"] = "SKIP_ROBOTS"
        return row
    captured = {"text": None}
    crawler = PlaywrightCrawler(
        headless=True,
        max_requests_per_crawl=1,
        max_request_retries=0,
        respect_robots_txt_file=True,
        retry_on_blocked=False,
        concurrency_settings=ConcurrencySettings(max_concurrency=1, desired_concurrency=1),
        request_handler_timeout=45,
    )

    @crawler.router.default_handler
    async def handler(context):
        captured["text"] = await context.page.locator("body").inner_text(timeout=8000)

    try:
        await crawler.run([source["url"]])
        if captured["text"] is None:
            row["status"] = "NO_CONTENT"
        else:
            row.update(signals(captured["text"], source["expected"]))
            row["status"] = "PASS" if row["expected_ratio"] >= 0.5 else "WEAK"
    except Exception as exc:
        row.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
    return row


async def main():
    static_results = []
    browser_results = []
    for source in load_sources():
        if not source.get("live"):
            static_results.append({"id": source["id"], "class": source["class"], "adapter": "crawlee-parsel", "status": "SKIP_POLICY", "reason": source.get("reason")})
            continue
        static_results.append(await fetch_parsel(source))
        if source.get("browser"):
            browser_results.append(await fetch_browser(source))
    write_results("crawlee-static", static_results)
    write_results("crawlee-browser", browser_results)


if __name__ == "__main__":
    asyncio.run(main())
