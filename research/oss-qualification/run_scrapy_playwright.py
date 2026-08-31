from __future__ import annotations

import scrapy
from scrapy.crawler import CrawlerProcess

from common import UA, load_sources, normalize_text, signals, write_results

RESULTS = []
BROWSER_SOURCES = [s for s in load_sources() if s.get("live") and s.get("browser")]


class BrowserQualificationSpider(scrapy.Spider):
    name = "ziras_browser_qualification"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 0.75,
        "RANDOMIZE_DOWNLOAD_DELAY": False,
        "RETRY_ENABLED": False,
        "USER_AGENT": UA,
        "LOG_LEVEL": "ERROR",
        "COOKIES_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "PLAYWRIGHT_MAX_PAGES_PER_CONTEXT": 1,
    }

    async def start(self):
        for source in BROWSER_SOURCES:
            yield scrapy.Request(
                source["url"],
                callback=self.parse,
                cb_kwargs={"source": source},
                meta={"playwright": True},
            )

    def parse(self, response, source):
        text = normalize_text(response.text)
        row = {
            "id": source["id"],
            "class": source["class"],
            "adapter": "scrapy-playwright",
            "http_status": response.status,
            "final_url": response.url,
        }
        row.update(signals(text, source["expected"]))
        row["status"] = "PASS" if response.status < 400 and row["expected_ratio"] >= 0.5 else "WEAK"
        RESULTS.append(row)


if __name__ == "__main__":
    process = CrawlerProcess(settings={"LOG_ENABLED": False})
    process.crawl(BrowserQualificationSpider)
    process.start()
    seen = {r["id"] for r in RESULTS}
    for source in BROWSER_SOURCES:
        if source["id"] not in seen:
            RESULTS.append({"id": source["id"], "class": source["class"], "adapter": "scrapy-playwright", "status": "SKIP_OR_FAILED", "reason": "No rendered response reached spider; robots denial or transport failure."})
    write_results("scrapy-playwright", RESULTS)
