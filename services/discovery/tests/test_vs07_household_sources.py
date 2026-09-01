from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

from ziras_discovery.adapters.public_web import PublicWebSignalAdapter, TextSignalConfig
from ziras_discovery.domain import SourceAccessMode, SourcePolicyScope
from ziras_discovery.source_catalog import build_policy_registry, load_source_catalog


NOW = datetime(2026, 8, 31, 20, 0, tzinfo=timezone.utc)

NEW_SOURCES = {
    "lidl_malta_poc_offers": "supermarket",
    "ax_sliema_dining_offers": "restaurant-direct",
    "esplora_family_promotions": "family-kids",
    "heritage_malta_activities": "activities-official",
    "active_ageing_discounts": "senior-benefits-official",
    "botika_personal_care_sale": "pharmacy-personal-care",
    "ax_verdala_wellness_offers": "spa-wellness",
}


def test_default_catalog_loads_all_household_poc_sources_fail_closed() -> None:
    entries = load_source_catalog()
    by_key = {entry.source_key: entry for entry in entries}

    for source_key, source_class in NEW_SOURCES.items():
        entry = by_key[source_key]
        assert entry.source_class == source_class
        assert entry.policy.mode is SourceAccessMode.ALLOW
        assert entry.policy.scope is SourcePolicyScope.POC
        assert entry.policy.robots_required is True
        assert entry.policy.content_storage_allowed is False
        assert entry.minimum_candidates == 1


def test_household_expansion_does_not_relax_existing_restricted_sources() -> None:
    entries = load_source_catalog()
    by_key = {entry.source_key: entry for entry in entries}
    registry = build_policy_registry(entries)

    assert by_key["lidl_malta_offers"].policy.scope is SourcePolicyScope.RESEARCH
    assert registry.decide(
        "lidl_malta_offers",
        scope=SourcePolicyScope.POC,
        source_url="https://www.lidl.com.mt/c/fresh-offers-every-week/s10038644",
    ).allowed is False

    assert registry.decide(
        "lidl_malta_poc_offers",
        scope=SourcePolicyScope.POC,
        source_url="https://www.lidl.com.mt/c/",
    ).allowed is True
    assert registry.decide(
        "lidl_malta_poc_offers",
        scope=SourcePolicyScope.PRODUCTION,
        source_url="https://www.lidl.com.mt/c/",
    ).allowed is False

    assert by_key["mcdonalds_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["pizzahut_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["franks_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["wolt_malta"].policy.mode is SourceAccessMode.PARTNER_ONLY


def test_custom_catalog_does_not_implicitly_load_default_poc_extensions(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        json.dumps(
            [
                {
                    "source_key": "fixture",
                    "display_name": "Fixture",
                    "source_class": "fixture",
                    "start_urls": ["https://example.com/offers"],
                    "fetch_mode": "static",
                    "adapter_kind": "promotion",
                    "policy": {
                        "mode": "allow",
                        "scope": "poc",
                        "reason": "fixture",
                        "allowed_path_prefixes": ["/offers"]
                    }
                }
            ]
        ),
        encoding="utf-8",
    )

    entries = load_source_catalog(catalog)
    assert [entry.source_key for entry in entries] == ["fixture"]


def test_explicit_extension_path_still_loads_only_the_requested_extension(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    extension = tmp_path / "extension.json"
    catalog.write_text("[]", encoding="utf-8")
    extension.write_text(
        json.dumps(
            [
                {
                    "source_key": "fixture_extension",
                    "display_name": "Fixture Extension",
                    "source_class": "fixture",
                    "start_urls": ["https://example.com/offers"],
                    "fetch_mode": "static",
                    "adapter_kind": "promotion",
                    "policy": {
                        "mode": "allow",
                        "scope": "poc",
                        "reason": "fixture",
                        "allowed_path_prefixes": ["/offers"]
                    }
                }
            ]
        ),
        encoding="utf-8",
    )

    entries = load_source_catalog(catalog, extension_path=extension)
    assert [entry.source_key for entry in entries] == ["fixture_extension"]


def test_family_promotion_heading_is_useful_but_generic_promotions_heading_is_not() -> None:
    html = """
    <html><body><main>
      <h1>Promotions</h1>
      <h2>Promotion 2: Free Family Entry</h2>
      <p>Spend €70 and receive admission for 2 adults and 2 children.</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter().extract(
        source_key="esplora_family_promotions",
        source_url="https://esplora.org.mt/promotions-tcs/",
        html=html,
        observed_at=NOW,
    )

    titles = [item.title for item in result.discoveries]
    assert "Promotion 2: Free Family Entry" in titles
    assert "Promotions" not in titles


def test_dining_offer_heading_produces_candidate_without_inventing_price() -> None:
    html = """
    <html><body><main>
      <h1>Penny Sundays Special Offer</h1>
      <p>Sunday lunch at Penny Black, Sliema.</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter().extract(
        source_key="ax_sliema_dining_offers",
        source_url="https://axhotelsmalta.com/victoria-hotel/special-offers/restaurants/penny-sundays/",
        html=html,
        observed_at=NOW,
    )

    assert [item.title for item in result.discoveries] == ["Penny Sundays Special Offer"]
    assert result.discoveries[0].current_price is None


def test_senior_discount_heading_produces_candidate() -> None:
    html = """
    <html><body><main>
      <h1>Discounts for the Elderly</h1>
      <h2>10% Discount at Example Pharmacy</h2>
      <p>Sliema - available to eligible 60+ residents.</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter().extract(
        source_key="active_ageing_discounts",
        source_url="https://aacc.gov.mt/en/discounts-for-the-elderly/",
        html=html,
        observed_at=NOW,
    )

    titles = [item.title for item in result.discoveries]
    assert "10% Discount at Example Pharmacy" in titles


def test_botika_sale_product_card_extracts_old_and_current_price() -> None:
    html = """
    <html><body><main>
      <h2>Family Sunscreen SPF50</h2>
      <p>€24.00 €18.00 Add to cart</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter().extract(
        source_key="botika_personal_care_sale",
        source_url="https://botika.mt/collections/sale",
        html=html,
        observed_at=NOW,
    )

    assert len(result.discoveries) == 1
    item = result.discoveries[0]
    assert item.title == "Family Sunscreen SPF50"
    assert item.original_price == Decimal("24.00")
    assert item.current_price == Decimal("18.00")


def test_wellness_package_heading_is_candidate_but_generic_voucher_heading_is_not() -> None:
    html = """
    <html><body><main>
      <h1>Gift Vouchers</h1>
      <h2>V SPA Day Pass Package</h2>
      <p>Access to the wellness facilities for two.</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter().extract(
        source_key="ax_verdala_wellness_offers",
        source_url="https://axhotelsmalta.com/gift-vouchers/",
        html=html,
        observed_at=NOW,
    )

    titles = [item.title for item in result.discoveries]
    assert "V SPA Day Pass Package" in titles
    assert "Gift Vouchers" not in titles


def test_heritage_activity_event_extracts_date() -> None:
    html = """
    <html><body><main>
      <h1>What's On</h1>
      <h2>Family Day at Fort St Elmo</h2>
      <p>6 September 2026</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter(TextSignalConfig(event_mode=True)).extract(
        source_key="heritage_malta_activities",
        source_url="https://heritagemalta.mt/whats-on/",
        html=html,
        observed_at=NOW,
    )

    assert len(result.discoveries) == 1
    assert result.discoveries[0].title == "Family Day at Fort St Elmo"


def test_vs07_source_pack_contains_no_secrets() -> None:
    source_pack = Path(__file__).parents[1] / "config" / "malta-source-vs07-poc.json"
    text = source_pack.read_text(encoding="utf-8").casefold()
    assert "access_token" not in text
    assert "password" not in text
    assert "api_key" not in text
