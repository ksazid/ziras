from __future__ import annotations

import asyncio

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

from common import UA, load_sources, normalize_text, robots_allowed, signals, write_results


async def main():
    results = []
    browser = BrowserConfig(
        browser_type="chromium",
        headless=True,
        user_agent=UA,
        user_agent_mode="",
        enable_stealth=False,
        proxy=None,
        text_mode=True,
        light_mode=True,
        verbose=False,
    )
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=30000,
        delay_before_return_html=1.0,
        remove_overlay_elements=False,
    )
    async with AsyncWebCrawler(config=browser) as crawler:
        for source in load_sources():
            row = {"id": source["id"], "class": source["class"], "adapter": "crawl4ai-browser"}
            if not source.get("live"):
                row.update(status="SKIP_POLICY", reason=source.get("reason"))
                results.append(row)
                continue
            if not source.get("browser"):
                row["status"] = "SKIP_NOT_BROWSER_SAMPLE"
                results.append(row)
                continue
            allowed, robots = robots_allowed(source["url"])
            row["robots"] = robots
            if not allowed:
                row["status"] = "SKIP_ROBOTS"
                results.append(row)
                continue
            try:
                result = await crawler.arun(source["url"], config=run_config)
                if not result.success:
                    row.update(status="ERROR", error=str(result.error_message or "crawl failed"))
                else:
                    html = result.cleaned_html or result.html or ""
                    text = normalize_text(html)
                    row.update(signals(text, source["expected"]))
                    row["status"] = "PASS" if row["expected_ratio"] >= 0.5 else "WEAK"
            except Exception as exc:
                row.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
            results.append(row)
    write_results("crawl4ai-browser", results)


if __name__ == "__main__":
    asyncio.run(main())
