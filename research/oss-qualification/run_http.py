from __future__ import annotations

import time
import httpx

from common import UA, load_sources, normalize_text, robots_allowed, signals, write_results


def main():
    results = []
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=20.0) as client:
        for source in load_sources():
            row = {"id": source["id"], "class": source["class"], "adapter": "httpx+bs4"}
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
                text = normalize_text(r.text)
                row.update(signals(text, source["expected"]))
                row["status"] = "PASS" if r.status_code < 400 and row["expected_ratio"] >= 0.5 else "WEAK"
            except Exception as exc:
                row.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
            results.append(row)
            time.sleep(0.75)
    write_results("http", results)


if __name__ == "__main__":
    main()
