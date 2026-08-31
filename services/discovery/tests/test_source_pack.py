from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from ziras_discovery.adapters.public_web import PublicWebSignalAdapter, TextSignalConfig
from ziras_discovery.domain import SourceAccessMode, SourcePolicyScope
from ziras_discovery.source_catalog import build_policy_registry, load_source_catalog


NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def test_malta_catalog_is_unique_and_fail_closed_for_blocked_sources() -> None:
    entries = load_source_catalog()
    keys = [entry.source_key for entry in entries]
    assert len(keys) == len(set(keys))
    assert len(entries) >= 10

    by_key = {entry.source_key: entry for entry in entries}
    assert by_key["mcdonalds_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["pizzahut_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["franks_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["wolt_malta"].policy.mode is SourceAccessMode.PARTNER_ONLY


def test_scope_and_path_controls_prevent_accidental_production_enablement() -> None:
    entries = load_source_catalog()
    registry = build_policy_registry(entries)

    research = registry.decide(
        "lidl_malta_offers",
        scope=SourcePolicyScope.RESEARCH,
        source_url="https://www.lidl.com.mt/c/fresh-offers-every-week/s10038644",
    )
    assert research.allowed is True

    production = registry.decide(
        "lidl_malta_offers",
        scope=SourcePolicyScope.PRODUCTION,
        source_url="https://www.lidl.com.mt/c/fresh-offers-every-week/s10038644",
    )
    assert production.allowed is False

    wrong_path = registry.decide(
        "lidl_malta_offers",
        scope=SourcePolicyScope.RESEARCH,
        source_url="https://www.lidl.com.mt/account",
    )
    assert wrong_path.allowed is False


def test_promotion_adapter_extracts_discounted_products_and_expiry_without_ai() -> None:
    html = """
    <html><body><main>
    <h1>Promotions</h1>
    <p>24.08 - 6.09</p>
    <h2>PLUM CAKE WITH YOGHURT</h2>
    <p>1.79 1.39 €</p>
    <h2>SEMI-SKIMMED MILK</h2>
    <p>1.35 0.99 €</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter().extract(
        source_key="fixture-supermarket",
        source_url="https://example.com/promotions",
        html=html,
        observed_at=NOW,
    )
    assert len(result.discoveries) == 2
    first = result.discoveries[0]
    assert first.title == "PLUM CAKE WITH YOGHURT"
    assert first.original_price == Decimal("1.79")
    assert first.current_price == Decimal("1.39")
    assert first.expires_at == datetime(2026, 9, 6, 23, 59, 59, tzinfo=timezone.utc)


def test_event_adapter_extracts_dated_event_without_ai() -> None:
    html = """
    <html><body><main>
    <h1>Events in Malta</h1>
    <h2>Valletta Night Festival</h2>
    <p>12 September 2026</p>
    </main></body></html>
    """
    result = PublicWebSignalAdapter(TextSignalConfig(event_mode=True)).extract(
        source_key="fixture-events",
        source_url="https://example.com/events",
        html=html,
        observed_at=NOW,
    )
    assert len(result.discoveries) == 1
    assert result.discoveries[0].title == "Valletta Night Festival"


def test_catalog_file_contains_no_secrets() -> None:
    path = Path(__file__).parents[1] / "config" / "malta-source-policy.json"
    text = path.read_text(encoding="utf-8").casefold()
    assert "access_token" not in text
    assert "password" not in text
