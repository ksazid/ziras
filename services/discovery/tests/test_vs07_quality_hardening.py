from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from ziras_discovery.adapters.public_web import PublicWebSignalAdapter, TextSignalConfig
from ziras_discovery.domain import SourcePolicyScope
from ziras_discovery.pipeline import _is_poc_quality_candidate
from ziras_discovery.source_catalog import FetchMode, load_source_catalog


NOW = datetime(2026, 9, 2, 9, 0, tzinfo=timezone.utc)


def test_visitmalta_uses_bounded_september_browser_inventory() -> None:
    entry = next(item for item in load_source_catalog() if item.source_key == "visitmalta_events")

    assert entry.fetch_mode is FetchMode.BROWSER
    assert entry.start_urls == (
        "https://www.visitmalta.com/en/events-in-malta-and-gozo/?startD=2026-09-01%2F&endD=2026-09-30%2F",
    )
    assert entry.policy.scope is SourcePolicyScope.POC


def test_numeric_event_date_is_extracted_without_locale_ambiguity() -> None:
    html = """
    <html><body><main>
      <h2>Breaking Borders</h2>
      <p>03/09/2026</p>
      <a href="/event/breaking-borders">Book Tickets</a>
    </main></body></html>
    """
    result = PublicWebSignalAdapter(TextSignalConfig(event_mode=True)).extract(
        source_key="visitmalta_events",
        source_url="https://www.visitmalta.com/en/events-in-malta-and-gozo/",
        html=html,
        observed_at=NOW,
    )

    item = next(discovery for discovery in result.discoveries if discovery.title == "Breaking Borders")
    assert item.starts_at is not None
    assert (item.starts_at.year, item.starts_at.month, item.starts_at.day) == (2026, 9, 3)


def test_lidl_named_eur_price_is_item_level_and_generic_shell_is_removed() -> None:
    html = """
    <html><body><main>
      <h1>Fresh offers every week!</h1>
      <p>Mantovano Melon PGI for EUR 1.49</p>
      <p>In store 27.08. - 02.09.</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter().extract(
        source_key="lidl_malta_poc_offers",
        source_url="https://www.lidl.com.mt/c/",
        html=html,
        observed_at=NOW,
    )

    assert len(result.discoveries) == 1
    item = result.discoveries[0]
    assert item.title == "Mantovano Melon PGI"
    assert item.current_price == Decimal("1.49")
    assert item.currency == "EUR"
    assert item.expires_at is not None
    assert (item.expires_at.month, item.expires_at.day) == (9, 2)


def test_esplora_generic_policy_and_numbered_promotion_noise_is_removed() -> None:
    html = """
    <html><body><main>
      <h2>Promotion 1:</h2>
      <h2>Promotion 2:</h2>
      <h2>Promotions T&amp;C's</h2>
      <h2>Not valid with any other offer or Group discount</h2>
      <h2>Family Admission Offer</h2>
      <p>Save 20% on a family admission package.</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter().extract(
        source_key="esplora_family_promotions",
        source_url="https://esplora.org.mt/promotions-tcs/",
        html=html,
        observed_at=NOW,
    )

    titles = {item.title for item in result.discoveries}
    assert "Family Admission Offer" in titles
    assert "Promotion 1:" not in titles
    assert "Promotion 2:" not in titles
    assert "Promotions T&C's" not in titles
    assert "Not valid with any other offer or Group discount" not in titles


def test_esplora_spend_thresholds_are_not_treated_as_sale_price_deltas() -> None:
    html = """
    <html><body><main>
      <h2>The Model Shop</h2>
      <p>Spend €35 and receive a benefit valued at €1.</p>
      <p>Spend €70 and receive a benefit valued at €2.</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter().extract(
        source_key="esplora_family_promotions",
        source_url="https://esplora.org.mt/promotions-tcs/",
        html=html,
        observed_at=NOW,
    )

    false_price_deltas = [
        item
        for item in result.discoveries
        if item.original_price is not None or item.current_price is not None
    ]
    assert false_price_deltas
    assert all(not _is_poc_quality_candidate(item) for item in false_price_deltas)


def test_heritage_store_navigation_is_not_an_event_candidate() -> None:
    html = """
    <html><body><main>
      <a href="/store/">Store</a>
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

    titles = {item.title for item in result.discoveries}
    assert titles == {"Family Day at Fort St Elmo"}


def test_dynamic_household_sources_remain_poc_only() -> None:
    entries = {entry.source_key: entry for entry in load_source_catalog()}

    for key in ("lidl_malta_poc_offers", "heritage_malta_activities", "botika_personal_care_sale"):
        assert entries[key].fetch_mode is FetchMode.BROWSER
        assert entries[key].policy.scope is SourcePolicyScope.POC


def test_poc_artifact_serializes_every_ranked_record() -> None:
    script = Path(__file__).parents[1] / "scripts" / "run_poc_ingestion.py"
    text = script.read_text(encoding="utf-8")

    assert "summary.ranked[:100]" not in text
    assert "for item in summary.ranked" in text
    assert '"ranked_record_count": len(summary.ranked)' in text
