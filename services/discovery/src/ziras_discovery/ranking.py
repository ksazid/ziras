from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Mapping, Sequence

from .domain import Discovery, FreshnessState


_FRESHNESS_WEIGHT = {
    FreshnessState.VERIFIED_LIVE: 40.0,
    FreshnessState.LIKELY_LIVE: 30.0,
    FreshnessState.UNVERIFIED: 10.0,
    FreshnessState.EXPIRED: -1000.0,
}


class DeterministicRanker:
    """Explainable MVP ranker. No model state or external service is required."""

    def rank(
        self,
        discoveries: Sequence[Discovery],
        *,
        context: dict[str, object],
    ) -> Sequence[Discovery]:
        now = _utc(context.get("now")) if isinstance(context.get("now"), datetime) else datetime.now(timezone.utc)
        interest_terms = tuple(
            str(value).casefold()
            for value in context.get("interest_terms", ())
            if str(value).strip()
        )
        raw_distances = context.get("distance_meters_by_entity", {})
        distances: Mapping[str, float] = raw_distances if isinstance(raw_distances, Mapping) else {}

        active = [item for item in discoveries if item.freshness is not FreshnessState.EXPIRED]
        return tuple(
            sorted(
                active,
                key=lambda item: (
                    -_score(item, now=now, interest_terms=interest_terms, distances=distances),
                    item.title.casefold(),
                    str(item.id),
                ),
            )
        )


def score_discovery(
    discovery: Discovery,
    *,
    now: datetime,
    interest_terms: Sequence[str] = (),
    distance_meters_by_entity: Mapping[str, float] | None = None,
) -> float:
    return _score(
        discovery,
        now=_utc(now),
        interest_terms=tuple(term.casefold() for term in interest_terms),
        distances=distance_meters_by_entity or {},
    )


def _score(
    discovery: Discovery,
    *,
    now: datetime,
    interest_terms: Sequence[str],
    distances: Mapping[str, float],
) -> float:
    score = _FRESHNESS_WEIGHT[discovery.freshness]

    observed_at = _utc(discovery.observed_at)
    age = max(timedelta(0), now - observed_at)
    if age <= timedelta(hours=6):
        score += 10.0
    elif age <= timedelta(hours=24):
        score += 6.0
    elif age <= timedelta(days=3):
        score += 2.0

    if discovery.original_price is not None and discovery.current_price is not None:
        original = Decimal(discovery.original_price)
        current = Decimal(discovery.current_price)
        if original > 0 and current < original:
            discount_percent = float((original - current) / original * 100)
            score += min(25.0, max(0.0, discount_percent / 2.0))

    if discovery.expires_at is not None:
        remaining = _utc(discovery.expires_at) - now
        if remaining <= timedelta(0):
            return -1000.0
        if remaining <= timedelta(hours=24):
            score += 20.0
        elif remaining <= timedelta(days=3):
            score += 12.0
        elif remaining <= timedelta(days=7):
            score += 6.0

    if discovery.starts_at is not None:
        until_start = _utc(discovery.starts_at) - now
        if timedelta(0) <= until_start <= timedelta(hours=24):
            score += 10.0
        elif timedelta(hours=24) < until_start <= timedelta(days=3):
            score += 6.0

    title = discovery.title.casefold()
    score += min(15.0, 5.0 * sum(1 for term in interest_terms if term and term in title))

    if discovery.entity_id is not None:
        distance = distances.get(str(discovery.entity_id))
        if distance is not None:
            if distance <= 1000:
                score += 15.0
            elif distance <= 3000:
                score += 10.0
            elif distance <= 10000:
                score += 5.0

    return score


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
