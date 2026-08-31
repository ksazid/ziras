from __future__ import annotations

import math
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


def parse_offer_date(raw: str, base: datetime):
    settings = {
        "RELATIVE_BASE": base,
        "PREFER_DATES_FROM": "future",
        "DATE_ORDER": "DMY",
        "IGNORE_SURROUNDING_TEXT": True,
    }
    parsed = dateparser.parse(raw, settings=settings)
    if parsed is None and raw.casefold().startswith("next "):
        parsed = dateparser.parse(raw[5:], settings=settings)
    return parsed


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def entity_match(left: dict, right: dict) -> dict:
    name_score = fuzz.token_set_ratio(norm_name(left["name"]), norm_name(right["name"]))
    category_compatible = left.get("category") == right.get("category")
    distance_m = haversine_m(left["coord"], right["coord"])
    same_external_id = bool(left.get("external_id") and left.get("external_id") == right.get("external_id"))
    matched = same_external_id or (name_score >= 90 and category_compatible and distance_m <= 350)
    return {
        "name_score": round(float(name_score), 2),
        "category_compatible": category_compatible,
        "distance_m": round(distance_m, 1),
        "same_external_id": same_external_id,
        "matched": matched,
    }


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
        ("Offer ends tomorrow", "2026-09-01"),
        ("next Sunday", "2026-09-06"),
    ]
    date_ok = True
    parsed_dates = []
    for raw, expected in date_cases:
        parsed = parse_offer_date(raw, base)
        actual = parsed.date().isoformat() if parsed else None
        parsed_dates.append({"raw": raw, "actual": actual, "expected": expected})
        date_ok &= actual == expected
    results.append({"id": "dateparser+cascade", "class": "freshness-date-normalization", "status": "PASS" if date_ok else "FAIL", "cases": parsed_dates})

    fixtures = [
        ("same-tikka", {"name": "Tikka Masala", "category": "indian-restaurant", "coord": (35.8976, 14.4610), "external_id": None}, {"name": "Tikka Masala Indian Bar and Restaurant", "category": "indian-restaurant", "coord": (35.8977, 14.4611), "external_id": None}, True),
        ("same-kups", {"name": "Kups Malta Birkirkara", "category": "korean-restaurant", "coord": (35.8971, 14.4620), "external_id": None}, {"name": "Kups Birkirkara - Korean Street Food", "category": "korean-restaurant", "coord": (35.8972, 14.4622), "external_id": None}, True),
        ("smart-name-collision", {"name": "Smart Supermarket Malta", "category": "supermarket", "coord": (35.9000, 14.4700), "external_id": None}, {"name": "Smart Mobility Malta", "category": "mobility", "coord": (35.9001, 14.4701), "external_id": None}, False),
        ("same-id-overrides-name-variation", {"name": "The Atrium", "category": "home-retail", "coord": (35.8890, 14.4720), "external_id": "osm:123"}, {"name": "Atrium Malta Home Furnishings", "category": "home-retail", "coord": (35.8892, 14.4723), "external_id": "osm:123"}, True),
    ]
    entity_ok = True
    entity_cases = []
    for case_id, left, right, expected in fixtures:
        outcome = entity_match(left, right)
        outcome.update({"case": case_id, "expected_match": expected})
        entity_cases.append(outcome)
        entity_ok &= outcome["matched"] == expected
    results.append({"id": "rapidfuzz+category+geo", "class": "entity-resolution-candidate-gate", "status": "PASS" if entity_ok else "FAIL", "cases": entity_cases, "note": "RapidFuzz is candidate similarity only; final identity requires category/geo or stable external identifiers."})

    write_results("core-ops", results)


if __name__ == "__main__":
    main()
