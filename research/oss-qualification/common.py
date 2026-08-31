from __future__ import annotations

import json
import re
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup

UA = "ZirasOSSQualification/0.1 (+https://github.com/ksazid/ziras)"
ROOT = Path(__file__).resolve().parent


def load_sources():
    return json.loads((ROOT / "sources.json").read_text())


def normalize_text(html: str) -> str:
    return " ".join(BeautifulSoup(html, "lxml").stripped_strings)


def signals(text: str, expected: list[str]) -> dict:
    lower = text.lower()
    hits = [x for x in expected if x.lower() in lower]
    return {
        "expected_hits": hits,
        "expected_ratio": round(len(hits) / max(1, len(expected)), 3),
        "has_euro_price": bool(re.search(r"€\s?\d+(?:[.,]\d+)?", text)),
        "has_percent": bool(re.search(r"\b\d{1,2}%", text)),
        "has_date_like": bool(re.search(r"\b(?:\d{1,2}[./-]\d{1,2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))", text, re.I)),
        "text_chars": len(text),
    }


def robots_allowed(url: str, timeout: float = 12.0) -> tuple[bool, str]:
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        r = httpx.get(robots_url, headers={"User-Agent": UA}, timeout=timeout, follow_redirects=True)
        if r.status_code == 404:
            return True, "robots_missing"
        if r.status_code >= 400:
            return False, f"robots_unavailable_{r.status_code}"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        rp.parse(r.text.splitlines())
        return rp.can_fetch(UA, url), "robots_checked"
    except Exception as exc:
        return False, f"robots_error:{type(exc).__name__}"


def write_results(name: str, results: list[dict]):
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps(results, indent=2, sort_keys=True))
