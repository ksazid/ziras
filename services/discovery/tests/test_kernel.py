from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from ziras_discovery.adapters.structured_html import StructuredHtmlAdapter
from ziras_discovery.domain import CanonicalEntity, FreshnessState, SourceAccessMode, SourcePolicy, should_accept_observation
from ziras_discovery.entity_resolution import score_entity_candidate
from ziras_discovery.extraction import parse_discovery_date
from ziras_discovery.freshness import FreshnessInput, classify_freshness
from ziras_discovery.policy import SourcePolicyRegistry


UTC = timezone.utc
NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


def test_unknown_source_fails_closed() -> None:
    registry = SourcePolicyRegistry()
    decision = registry.decide("unknown.example")
    assert decision.allowed is False
    assert decision.mode is SourceAccessMode.DENY


def test_user_share_only_requires_user_share() -> None:
    registry = SourcePolicyRegistry(
        {
            "closed.example": SourcePolicy(
                source_key="closed.example",
                mode=SourceAccessMode.USER_SHARE_ONLY,
                reason="Only user-shared ingestion is approved.",
            )
        }
    )
    assert registry.decide("closed.example").allowed is False
    assert registry.decide("closed.example", user_shared=True).allowed is True


def test_explicit_expiry_always_wins() -> None:
    state = classify_freshness(
        FreshnessInput(
            observed_at=NOW - timedelta(minutes=5),
            verified_at=NOW - timedelta(minutes=2),
            explicitly_active=True,
            expires_at=NOW - timedelta(seconds=1),
            now=NOW,
        )
    )
    assert state is FreshnessState.EXPIRED


def test_past_event_occurrence_does_not_revive_when_observed_today() -> None:
    state = classify_freshness(
        FreshnessInput(
            observed_at=NOW - timedelta(minutes=5),
            starts_at=NOW - timedelta(days=2),
            now=NOW,
            is_event=True,
        )
    )
    assert state is FreshnessState.EXPIRED


def test_non_event_valid_from_date_does_not_imply_expiry() -> None:
    state = classify_freshness(
        FreshnessInput(
            observed_at=NOW - timedelta(minutes=5),
            starts_at=NOW - timedelta(days=2),
            now=NOW,
            is_event=False,
        )
    )
    assert state is FreshnessState.LIKELY_LIVE


def test_newer_observation_only() -> None:
    current = NOW
    assert should_accept_observation(current_observed_at=current, incoming_observed_at=NOW + timedelta(seconds=1))
    assert not should_accept_observation(current_observed_at=current, incoming_observed_at=NOW)
    assert not should_accept_observation(current_observed_at=current, incoming_observed_at=NOW - timedelta(seconds=1))


def test_smart_supermarket_does_not_merge_with_smart_mobility() -> None:
    supermarket = CanonicalEntity(id=uuid4(), name="Smart Supermarket", category="supermarket")
    mobility = CanonicalEntity(id=uuid4(), name="Smart Mobility", category="mobility")
    result = score_entity_candidate(supermarket, mobility)
    assert result.auto_merge is False
    assert "category_conflict" in result.signals


def test_same_restaurant_with_geo_and_category_can_merge() -> None:
    left = CanonicalEntity(
        id=uuid4(),
        name="Tikka Masala Indian Bar and Restaurant",
        category="indian_restaurant",
        latitude=35.8972,
        longitude=14.4617,
    )
    right = CanonicalEntity(
        id=uuid4(),
        name="Tikka Masala Indian Restaurant",
        category="indian_restaurant",
        latitude=35.89725,
        longitude=14.46172,
    )
    result = score_entity_candidate(left, right)
    assert result.auto_merge is True


def test_deterministic_next_weekday_date() -> None:
    parsed = parse_discovery_date("next Sunday", observed_at=NOW)
    assert parsed == datetime(2026, 9, 6, 0, 0, tzinfo=UTC)


def test_structured_html_adapter_extracts_product_offer_without_ai() -> None:
    html = """
    <html><head>
      <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Noise Cancelling Headphones",
        "offers": {
          "@type": "Offer",
          "price": "149.99",
          "priceCurrency": "EUR",
          "priceValidUntil": "2026-09-10"
        }
      }
      </script>
    </head><body></body></html>
    """
    result = StructuredHtmlAdapter().extract(
        source_key="fixture-retailer",
        source_url="https://example.com/headphones",
        html=html,
        observed_at=NOW,
        content_hash="abc123",
    )
    assert result.observation.adapter == "structured-html-v1"
    assert len(result.discoveries) == 1
    discovery = result.discoveries[0]
    assert discovery.title == "Noise Cancelling Headphones"
    assert discovery.current_price == Decimal("149.99")
    assert discovery.currency == "EUR"
    assert discovery.expires_at == datetime(2026, 9, 10, 0, 0, tzinfo=UTC)
