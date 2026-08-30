from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from rapidfuzz.fuzz import WRatio

from .domain import CanonicalEntity


@dataclass(frozen=True, slots=True)
class EntityCandidateScore:
    score: float
    auto_merge: bool
    signals: tuple[str, ...]


def score_entity_candidate(left: CanonicalEntity, right: CanonicalEntity) -> EntityCandidateScore:
    external_match = _shared_external_id(left, right)
    if external_match:
        return EntityCandidateScore(1.0, True, ("external_id",))

    name_score = WRatio(_norm(left.name), _norm(right.name)) / 100.0
    category_match = bool(left.category and right.category and _norm(left.category) == _norm(right.category))
    category_conflict = bool(left.category and right.category and not category_match)
    distance_m = _distance_m(left, right)
    geo_match = distance_m is not None and distance_m <= 150
    address_match = bool(left.address and right.address and WRatio(_norm(left.address), _norm(right.address)) >= 90)

    score = name_score * 0.55
    signals: list[str] = [f"name:{name_score:.3f}"]

    if category_match:
        score += 0.2
        signals.append("category")
    elif category_conflict:
        score -= 0.25
        signals.append("category_conflict")

    if geo_match:
        score += 0.15
        signals.append("geo")
    if address_match:
        score += 0.15
        signals.append("address")

    score = max(0.0, min(1.0, score))
    corroborating = sum((category_match, geo_match, address_match))
    auto_merge = name_score >= 0.82 and corroborating >= 1 and score >= 0.78 and not category_conflict
    return EntityCandidateScore(round(score, 4), auto_merge, tuple(signals))


def _shared_external_id(left: CanonicalEntity, right: CanonicalEntity) -> bool:
    for namespace, value in left.external_ids.items():
        if value and right.external_ids.get(namespace) == value:
            return True
    return False


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _distance_m(left: CanonicalEntity, right: CanonicalEntity) -> float | None:
    if None in (left.latitude, left.longitude, right.latitude, right.longitude):
        return None
    lat1, lon1, lat2, lon2 = map(radians, (left.latitude, left.longitude, right.latitude, right.longitude))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(a))
