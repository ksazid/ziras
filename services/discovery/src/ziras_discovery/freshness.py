from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .domain import FreshnessState


@dataclass(frozen=True, slots=True)
class FreshnessInput:
    observed_at: datetime
    now: datetime
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    explicitly_active: bool = False
    verified_at: datetime | None = None


def classify_freshness(value: FreshnessInput) -> FreshnessState:
    now = _utc(value.now)
    observed_at = _utc(value.observed_at)
    expires_at = _utc(value.expires_at) if value.expires_at else None
    starts_at = _utc(value.starts_at) if value.starts_at else None
    verified_at = _utc(value.verified_at) if value.verified_at else None

    # Expiry is absolute: relevance/value cannot override an explicit expiry.
    if expires_at is not None and expires_at <= now:
        return FreshnessState.EXPIRED

    if starts_at is not None and starts_at > now:
        return FreshnessState.UNVERIFIED

    if value.explicitly_active and verified_at is not None and now - verified_at <= timedelta(hours=24):
        return FreshnessState.VERIFIED_LIVE

    if now - observed_at <= timedelta(hours=24):
        return FreshnessState.LIKELY_LIVE

    return FreshnessState.UNVERIFIED


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
