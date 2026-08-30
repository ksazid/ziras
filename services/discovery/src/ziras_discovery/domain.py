from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Mapping, Sequence
from uuid import UUID


class SourceAccessMode(StrEnum):
    ALLOW = "allow"
    PARTNER_ONLY = "partner_only"
    USER_SHARE_ONLY = "user_share_only"
    DENY = "deny"


class FreshnessState(StrEnum):
    VERIFIED_LIVE = "verified_live"
    LIKELY_LIVE = "likely_live"
    UNVERIFIED = "unverified"
    EXPIRED = "expired"


class DiscoveryType(StrEnum):
    DEAL = "deal"
    OPENING = "opening"
    EVENT = "event"
    PRICE_DROP = "price_drop"
    NEW_PRODUCT = "new_product"
    NEW_MENU = "new_menu"
    HAPPY_HOUR = "happy_hour"
    TRENDING = "trending"


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    source_key: str
    mode: SourceAccessMode
    reason: str
    policy_url: str | None = None
    robots_required: bool = True
    reviewed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SourceObservation:
    id: UUID
    source_key: str
    source_url: str
    observed_at: datetime
    content_hash: str
    extracted: Mapping[str, object]
    http_status: int | None = None
    adapter: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalEntity:
    id: UUID
    name: str
    category: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    external_ids: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Evidence:
    source_observation_id: UUID
    source_url: str
    observed_at: datetime
    field_name: str
    raw_value: str
    confidence: float


@dataclass(frozen=True, slots=True)
class Discovery:
    id: UUID
    discovery_type: DiscoveryType
    entity_id: UUID | None
    title: str
    source_key: str
    source_url: str
    observed_at: datetime
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    original_price: Decimal | None = None
    current_price: Decimal | None = None
    currency: str | None = None
    freshness: FreshnessState = FreshnessState.UNVERIFIED
    evidence: Sequence[Evidence] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Interest:
    key: str
    weight: float
    parent_key: str | None = None


@dataclass(frozen=True, slots=True)
class Interaction:
    subject_id: UUID
    discovery_id: UUID
    event_type: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class Watch:
    id: UUID
    subject_id: UUID
    query: str
    radius_meters: int | None = None
    minimum_discount_percent: int | None = None
    enabled: bool = True


def should_accept_observation(
    *, current_observed_at: datetime | None, incoming_observed_at: datetime
) -> bool:
    """Prevent a late/older crawl from replacing newer source state."""
    return current_observed_at is None or incoming_observed_at > current_observed_at
