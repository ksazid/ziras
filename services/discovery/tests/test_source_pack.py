from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import pytest

from ziras_discovery.adapters.public_web import PublicWebSignalAdapter, TextSignalConfig
from ziras_discovery.domain import SourceAccessMode, SourcePolicyScope
from ziras_discovery.source_catalog import AdapterKind, build_policy_registry, load_source_catalog


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

    for source_key, source_url in (
        ("spazju_kreattiv_events", "https://spazjukreattiv.org/events/list/"),
        ("eurosport_malta_sale", "https://www.eurosport.com.mt/sale"),
    ):
        assert registry.decide(
            source_key,
            scope=SourcePolicyScope.POC,
            source_url=source_url,
        ).allowed is True
        assert registry.decide(
            source_key,
            scope=SourcePolicyScope.PRODUCTION,
            source_url=source_url,
        ).allowed is False


def test_vs06_hardening_applies_route_semantics_without_changing_policy() -> None:
    entries = load_source_catalog()
    by_key = {entry.source_key: entry for entry in entries}

    visitmalta = by_key["visitmalta_events"]
    eden = by_key["eden_cinemas"]

    assert visitmalta.minimum_candidates == 1
    assert visitmalta.policy.scope is SourcePolicyScope.POC
    assert visitmalta.policy.mode is SourceAccessMode.ALLOW

    assert eden.adapter_kind_for("https://www.edencinemas.com.mt/special-offers") is AdapterKind.PROMOTION
    assert eden.adapter_kind_for("https://www.edencinemas.com.mt/whats-on") is AdapterKind.EVENT
    assert eden.policy.scope is SourcePolicyScope.POC
    assert eden.policy.mode is SourceAccessMode.ALLOW


def test_hardening_overlay_rejects_policy_or_url_mutation(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    hardening = tmp_path / "hardening.json"
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
    hardening.write_text(
        json.dumps({"fixture": {"policy": {"mode": "production"}}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot mutate policy/catalog authority"):
        load_source_catalog(catalog, hardening_path=hardening)


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


def test_catalog_files_contain_no_secrets() -> None:
    config_dir = Path(__file__).parents[1] / "config"
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            config_dir / "malta-source-policy.json",
            config_dir / "malta-source-vs06-poc.json",
            config_dir / "malta-source-hardening.json",
        )
    ).casefold()
    assert "access_token" not in text
    assert "password" not in text
