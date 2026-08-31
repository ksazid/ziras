from __future__ import annotations

import time

import extruct
import httpx
import trafilatura

from common import UA, load_sources, normalize_text, robots_allowed, signals, write_results


def structured_counts(html: str, base_url: str) -> dict:
    try:
        data = extruct.extract(
            html,
            base_url=base_url,
            syntaxes=["json-ld", "microdata", "opengraph"],
            errors="ignore",
        )
        counts = {key: len(data.get(key, [])) for key in ("json-ld", "microdata", "opengraph")}
        counts["total"] = sum(counts.values())
        return counts
    except Exception:
        return {"json-ld": 0, "microdata": 0, "opengraph": 0, "total": 0}


def main():
    results = []
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=20.0) as client:
        for source in load_sources():
            row = {"id": source["id"], "class": source["class"], "adapter": "httpx+bs4"}
            if source.get("freshnessControl"):
                row["freshness_control"] = source["freshnessControl"]
            if not source.get("live"):
                row.update(status="SKIP_POLICY", reason=source.get("reason"))
                results.append(row)
                continue
            allowed, robots = robots_allowed(source["url"])
            row["robots"] = robots
            if not allowed:
                row["status"] = "SKIP_ROBOTS"
                results.append(row)
                continue
            try:
                r = client.get(source["url"])
                row["http_status"] = r.status_code
                row["final_url"] = str(r.url)
                text = normalize_text(r.text)
                row.update(signals(text, source["expected"]))
                row["structured_metadata"] = structured_counts(r.text, str(r.url))
                clean = trafilatura.extract(r.text, url=str(r.url), include_links=False, include_images=False)
                row["clean_text_chars"] = len(clean or "")
                row["status"] = "PASS" if r.status_code < 400 and row["expected_ratio"] >= 0.5 else "WEAK"
            except Exception as exc:
                row.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
            results.append(row)
            time.sleep(0.75)
    write_results("http", results)


if __name__ == "__main__":
    main()
