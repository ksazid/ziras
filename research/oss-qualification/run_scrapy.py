from __future__ import annotations

import scrapy
from scrapy.crawler import CrawlerProcess

from common import UA, load_sources, normalize_text, signals, write_results

RESULTS = []
LIVE_SOURCES = [s for s in load_sources() if s.get("live")]


class QualificationSpider(scrapy.Spider):
    name = "ziras_qualification"
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
    }

    async def start(self):
        for source in LIVE_SOURCES:
            yield scrapy.Request(source["url"], callback=self.parse, cb_kwargs={"source": source})

    def parse(self, response, source):
        text = normalize_text(response.text)
        row = {
            "id": source["id"],
            "class": source["class"],
            "adapter": "scrapy",
            "http_status": response.status,
            "final_url": response.url,
        }
        row.update(signals(text, source["expected"]))
        row["status"] = "PASS" if response.status < 400 and row["expected_ratio"] >= 0.5 else "WEAK"
        RESULTS.append(row)


if __name__ == "__main__":
    skipped = [
        {"id": s["id"], "class": s["class"], "adapter": "scrapy", "status": "SKIP_POLICY", "reason": s.get("reason")}
        for s in load_sources() if not s.get("live")
    ]
    process = CrawlerProcess(settings={"LOG_ENABLED": False})
    process.crawl(QualificationSpider)
    process.start()
    seen = {r["id"] for r in RESULTS}
    for source in LIVE_SOURCES:
        if source["id"] not in seen:
            RESULTS.append({"id": source["id"], "class": source["class"], "adapter": "scrapy", "status": "SKIP_OR_FAILED", "reason": "No response reached spider; robots denial or transport failure."})
    write_results("scrapy", skipped + RESULTS)
