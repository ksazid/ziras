from __future__ import annotations

import re
from datetime import datetime

import dateparser
from price_parser import Price
from rapidfuzz import fuzz

from common import write_results


def norm_name(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"\b(malta|restaurant|bar|and|the|street food|supermarket)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def main():
    results = []

    price_cases = [
        ("€5.49", "5.49", "€"),
        ("22,90 €", "22.90", "€"),
        ("AED 39", "39", "AED"),
        ("SAR 200.50", "200.50", "SAR"),
    ]
    price_ok = True
    parsed_prices = []
    for raw, amount, currency in price_cases:
        parsed = Price.fromstring(raw)
        parsed_prices.append({"raw": raw, "amount": str(parsed.amount), "currency": parsed.currency})
        price_ok &= str(parsed.amount) == amount and parsed.currency == currency
    results.append({"id": "price-parser", "class": "price-normalization", "status": "PASS" if price_ok else "FAIL", "cases": parsed_prices})

    base = datetime(2026, 8, 31, 0, 0, 0)
    date_cases = [
        ("December 31st, 2026", "2026-12-31"),
        ("31/08/2026", "2026-08-31"),
        ("next Sunday", "2026-09-06"),
    ]
    date_ok = True
    parsed_dates = []
    settings = {"RELATIVE_BASE": base, "PREFER_DATES_FROM": "future", "DATE_ORDER": "DMY"}
    for raw, expected in date_cases:
        parsed = dateparser.parse(raw, settings=settings)
        actual = parsed.date().isoformat() if parsed else None
        parsed_dates.append({"raw": raw, "actual": actual, "expected": expected})
        date_ok &= actual == expected
    results.append({"id": "dateparser", "class": "freshness-date-normalization", "status": "PASS" if date_ok else "FAIL", "cases": parsed_dates})

    positive_pairs = [
        ("Tikka Masala", "Tikka Masala Indian Bar and Restaurant", 95),
        ("Kups Malta Birkirkara", "Kups Birkirkara - Korean Street Food", 90),
        ("Eden Cinemas", "EDEN Cinemas Malta", 95),
    ]
    negative_pairs = [
        ("Smart Supermarket Malta", "Smart Mobility Malta", 80),
        ("Tikka Masala", "Malta Discount Card", 70),
    ]
    comparisons = []
    entity_ok = True
    for left, right, threshold in positive_pairs:
        score = fuzz.token_set_ratio(norm_name(left), norm_name(right))
        comparisons.append({"left": left, "right": right, "score": score, "rule": f">={threshold}"})
        entity_ok &= score >= threshold
    for left, right, ceiling in negative_pairs:
        score = fuzz.token_set_ratio(norm_name(left), norm_name(right))
        comparisons.append({"left": left, "right": right, "score": score, "rule": f"<{ceiling}"})
        entity_ok &= score < ceiling
    results.append({"id": "rapidfuzz", "class": "entity-name-candidate-generation", "status": "PASS" if entity_ok else "FAIL", "cases": comparisons})

    write_results("core-ops", results)


if __name__ == "__main__":
    main()
