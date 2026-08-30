from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from ..domain import Discovery, DiscoveryType, FreshnessState, SourceObservation
from ..extraction import extract_structured_items, first_value, parse_discovery_date, parse_money


@dataclass(frozen=True, slots=True)
class StructuredHtmlResult:
    observation: SourceObservation
    discoveries: tuple[Discovery, ...]


class StructuredHtmlAdapter:
    name = "structured-html-v1"

    def extract(
        self,
        *,
        source_key: str,
        source_url: str,
        html: str,
        observed_at: datetime,
        content_hash: str,
    ) -> StructuredHtmlResult:
        items = extract_structured_items(html, base_url=source_url)
        observation = SourceObservation(
            id=uuid4(),
            source_key=source_key,
            source_url=source_url,
            observed_at=observed_at,
            content_hash=content_hash,
            extracted={"structured_item_count": len(items)},
            adapter=self.name,
        )
        discoveries: list[Discovery] = []

        for item in items:
            discovery = self._to_discovery(item, source_key=source_key, source_url=source_url, observed_at=observed_at)
            if discovery is not None:
                discoveries.append(discovery)

        return StructuredHtmlResult(observation=observation, discoveries=tuple(discoveries))

    def _to_discovery(
        self,
        item: dict[str, Any],
        *,
        source_key: str,
        source_url: str,
        observed_at: datetime,
    ) -> Discovery | None:
        raw_type = first_value(item, "@type", "type")
        types = {str(value).casefold() for value in (raw_type if isinstance(raw_type, list) else [raw_type]) if value}

        title = first_value(item, "name", "headline", "title")
        if not title:
            return None

        offer = item.get("offers")
        if isinstance(offer, list):
            offer = offer[0] if offer else None
        if not isinstance(offer, dict):
            offer = item if "offer" in types else None

        discovery_type = _map_type(types, offer)
        if discovery_type is None:
            return None

        price_value = first_value(offer or {}, "price", "lowPrice")
        amount, currency = parse_money(price_value)
        if amount and not currency:
            currency = first_value(offer or {}, "priceCurrency")

        starts_at = parse_discovery_date(first_value(item, "startDate", "validFrom"), observed_at=observed_at)
        expires_at = parse_discovery_date(
            first_value(offer or {}, "priceValidUntil", "validThrough") or first_value(item, "endDate", "validThrough"),
            observed_at=observed_at,
        )

        return Discovery(
            id=uuid4(),
            discovery_type=discovery_type,
            entity_id=None,
            title=str(title).strip(),
            source_key=source_key,
            source_url=source_url,
            observed_at=observed_at,
            starts_at=starts_at,
            expires_at=expires_at,
            current_price=amount,
            currency=str(currency) if currency else None,
            freshness=FreshnessState.UNVERIFIED,
        )


def _map_type(types: set[str], offer: dict[str, Any] | None) -> DiscoveryType | None:
    if "event" in types:
        return DiscoveryType.EVENT
    if "restaurant" in types or "foodestablishment" in types:
        return DiscoveryType.NEW_MENU if offer else None
    if "product" in types:
        return DiscoveryType.DEAL if offer else DiscoveryType.NEW_PRODUCT
    if "offer" in types or offer:
        return DiscoveryType.DEAL
    return None
