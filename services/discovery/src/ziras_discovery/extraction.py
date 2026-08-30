from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import dateparser
import extruct
from price_parser import Price


_WEEKDAYS = {name: index for index, name in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"))}


def extract_structured_items(html: str, *, base_url: str) -> list[dict[str, Any]]:
    payload = extruct.extract(html, base_url=base_url, syntaxes=["json-ld", "microdata", "opengraph"], uniform=True)
    items: list[dict[str, Any]] = []
    for syntax in ("json-ld", "microdata"):
        for value in payload.get(syntax, []):
            items.extend(_flatten(value))
    return [item for item in items if isinstance(item, dict)]


def parse_money(value: object) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    parsed = Price.fromstring(str(value))
    amount = str(parsed.amount) if parsed.amount is not None else None
    return amount, parsed.currency


def parse_discovery_date(value: object, *, observed_at: datetime) -> datetime | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    normalized_base = _utc(observed_at)
    lowered = raw.casefold()
    if lowered == "today":
        return normalized_base.replace(hour=0, minute=0, second=0, microsecond=0)
    if lowered == "tomorrow":
        return (normalized_base + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    if lowered.startswith("next ") and lowered[5:] in _WEEKDAYS:
        target = _WEEKDAYS[lowered[5:]]
        days = (target - normalized_base.weekday()) % 7
        days = 7 if days == 0 else days
        return (normalized_base + timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)

    parsed = dateparser.parse(
        raw,
        settings={
            "RELATIVE_BASE": normalized_base.replace(tzinfo=None),
            "RETURN_AS_TIMEZONE_AWARE": True,
            "TIMEZONE": "UTC",
            "TO_TIMEZONE": "UTC",
            "PREFER_DATES_FROM": "future",
        },
    )
    return _utc(parsed) if parsed else None


def first_value(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, "", []):
            return value
    return None


def _flatten(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from _flatten(item)
        return
    if not isinstance(value, dict):
        return
    yield value
    graph = value.get("@graph")
    if graph is not None:
        yield from _flatten(graph)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
