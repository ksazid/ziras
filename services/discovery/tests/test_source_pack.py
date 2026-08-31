from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ziras_discovery.adapters.source_pack import (
    PolicyStage,
    SOURCE_PROFILES,
    SourcePackAdapter,
    SourcePackError,
    candidate_policy_registry,
)
from ziras_discovery.domain import DiscoveryType, SourceAccessMode, SourcePolicy
from ziras_discovery.policy import SourcePolicyRegistry


NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

EVENT_HTML = """
<html><head><script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Event",
  "name": "Harbour Nights Malta",
  "startDate": "2026-09-05T20:00:00+02:00",
  "endDate": "2026-09-05T23:00:00+02:00",
  "url": "https://www.visitmalta.com/en/events-in-malta-and-gozo/event/harbour-nights/"
}
</script></head><body></body></html>
"""

PRODUCT_HTML = """
<html><head><script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Example Headphones",
  "offers": {
    "@type": "Offer",
    "price": "149.99",
    "priceCurrency": "EUR",
    "priceValidUntil": "2026-09-07"
  }
}
</script></head><body></body></html>
"""

DEAL_HTML = """
<html><head><script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Offer",
  "name": "30% off dinner",
  "price": "21",
  "priceCurrency": "EUR",
  "priceValidUntil": "2026-09-03"
}
</script></head><body></body></html>
"""


def test_pack_has_broad_malta_source_classes() -> None:
    assert set(SOURCE_PROFILES) == {
        "visitmalta_events",
        "deal_mt",
        "scan_malta",
        "greens_malta",
        "decathlon_malta",
        "atrium_malta",
        "pizza_hut_malta",
        "shows_happening",
    }
    assert SOURCE_PROFILES["visitmalta_events"].policy_stage is PolicyStage.REVIEW_REQUIRED
    assert SOURCE_PROFILES["deal_mt"].policy_stage is PolicyStage.PARTNER_REQUIRED
    assert SOURCE_PROFILES["shows_happening"].policy_stage is PolicyStage.PARTNER_REQUIRED


def test_candidate_registry_denies_review_and_partner_candidates() -> None:
    pack = SourcePackAdapter(candidate_policy_registry())
    for source_key in ("visitmalta_events", "deal_mt", "shows_happening"):
        assert pack.readiness(source_key).allowed is False
        assert pack.readiness(source_key, partner=True).allowed is False
        assert pack.readiness(source_key).mode is SourceAccessMode.DENY


def test_review_required_source_cannot_extract_without_explicit_policy() -> None:
    pack = SourcePackAdapter(candidate_policy_registry())
    with pytest.raises(SourcePackError, match="policy denied"):
        pack.extract(
            source_key="visitmalta_events",
            source_url="https://www.visitmalta.com/en/events-in-malta-and-gozo/",
            html=EVENT_HTML,
            observed_at=NOW,
            content_hash="event-hash",
        )


def test_partner_source_needs_explicit_partner_policy_and_partner_context() -> None:
    registry = candidate_policy_registry()
    registry.register(
        SourcePolicy(
            source_key="deal_mt",
            mode=SourceAccessMode.PARTNER_ONLY,
            reason="Test-only approved partner feed/web access.",
            robots_required=True,
            reviewed_at=NOW,
        )
    )
    pack = SourcePackAdapter(registry)
    assert pack.readiness("deal_mt").allowed is False
    assert pack.readiness("deal_mt", partner=True).allowed is True

    with pytest.raises(SourcePackError, match="Partner access required"):
        pack.extract(
            source_key="deal_mt",
            source_url="https://deal.com.mt/",
            html=DEAL_HTML,
            observed_at=NOW,
            content_hash="deal-hash",
        )

    result = pack.extract(
        source_key="deal_mt",
        source_url="https://deal.com.mt/",
        html=DEAL_HTML,
        observed_at=NOW,
        content_hash="deal-hash",
        partner=True,
    )
    assert len(result.discoveries) == 1
    assert result.discoveries[0].discovery_type is DiscoveryType.DEAL
    assert result.observation.extracted["policy_mode"] == SourceAccessMode.PARTNER_ONLY.value


def test_explicit_policy_approval_enables_visitmalta_fixture() -> None:
    registry = candidate_policy_registry()
    registry.register(
        SourcePolicy(
            source_key="visitmalta_events",
            mode=SourceAccessMode.ALLOW,
            reason="Test-only explicit policy approval.",
            policy_url="https://www.visitmalta.com/en/terms-and-conditions/",
            robots_required=True,
            reviewed_at=NOW,
        )
    )
    pack = SourcePackAdapter(registry)
    result = pack.extract(
        source_key="visitmalta_events",
        source_url="https://www.visitmalta.com/en/events-in-malta-and-gozo/",
        html=EVENT_HTML,
        observed_at=NOW,
        content_hash="event-hash",
    )
    assert result.observation.adapter == "source-pack-v1"
    assert result.observation.extracted["source_profile"] == "visitmalta_events"
    assert len(result.discoveries) == 1
    assert result.discoveries[0].discovery_type is DiscoveryType.EVENT


def test_explicit_retail_policy_uses_shared_structured_extractor() -> None:
    registry = SourcePolicyRegistry(
        {
            "scan_malta": SourcePolicy(
                source_key="scan_malta",
                mode=SourceAccessMode.ALLOW,
                reason="Test-only explicit policy approval.",
                robots_required=True,
                reviewed_at=NOW,
            )
        }
    )
    pack = SourcePackAdapter(registry)
    result = pack.extract(
        source_key="scan_malta",
        source_url="https://www.scanmalta.com/shop/example-headphones.html",
        html=PRODUCT_HTML,
        observed_at=NOW,
        content_hash="product-hash",
    )
    assert len(result.discoveries) == 1
    assert result.discoveries[0].discovery_type is DiscoveryType.DEAL
    assert str(result.discoveries[0].current_price) == "149.99"
    assert result.discoveries[0].currency == "EUR"


def test_foreign_host_and_non_https_are_rejected_even_with_policy() -> None:
    registry = SourcePolicyRegistry(
        {
            "visitmalta_events": SourcePolicy(
                source_key="visitmalta_events",
                mode=SourceAccessMode.ALLOW,
                reason="Test-only explicit policy approval.",
            )
        }
    )
    pack = SourcePackAdapter(registry)
    for bad_url in (
        "https://example.com/en/events-in-malta-and-gozo/",
        "http://www.visitmalta.com/en/events-in-malta-and-gozo/",
    ):
        with pytest.raises(SourcePackError, match="outside the approved domain"):
            pack.extract(
                source_key="visitmalta_events",
                source_url=bad_url,
                html=EVENT_HTML,
                observed_at=NOW,
                content_hash="bad-hash",
            )


def test_unknown_source_is_fail_closed() -> None:
    pack = SourcePackAdapter(candidate_policy_registry())
    with pytest.raises(SourcePackError, match="Unknown source profile"):
        pack.readiness("unknown_source")


def test_duplicate_structured_items_are_removed() -> None:
    inner_head = PRODUCT_HTML.split("<head>", 1)[1].split("</head>", 1)[0]
    duplicate_html = PRODUCT_HTML.replace("</head>", inner_head + "</head>", 1)
    registry = SourcePolicyRegistry(
        {
            "greens_malta": SourcePolicy(
                source_key="greens_malta",
                mode=SourceAccessMode.ALLOW,
                reason="Test-only explicit policy approval.",
                robots_required=True,
            )
        }
    )
    pack = SourcePackAdapter(registry)
    result = pack.extract(
        source_key="greens_malta",
        source_url="https://www.greens.com.mt/product/example",
        html=duplicate_html,
        observed_at=NOW,
        content_hash="dup-hash",
    )
    assert len(result.discoveries) == 1
