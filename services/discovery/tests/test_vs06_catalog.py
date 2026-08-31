from __future__ import annotations

from pathlib import Path

import pytest

from ziras_discovery.domain import SourceAccessMode, SourcePolicyScope
from ziras_discovery.source_catalog import AdapterKind, FetchMode, load_source_catalog


def test_default_catalog_applies_hardening_and_reaches_five_poc_source_classes() -> None:
    entries = load_source_catalog()
    by_key = {entry.source_key: entry for entry in entries}

    poc = [
        entry
        for entry in entries
        if entry.policy.mode is SourceAccessMode.ALLOW
        and entry.policy.scope is SourcePolicyScope.POC
    ]
    classes = {entry.source_class for entry in poc}

    assert {
        "events-official",
        "entertainment-offers",
        "home-retail",
        "cultural-venue-events",
        "sports-retail",
    }.issubset(classes)
    assert len(classes) >= 5

    eden = by_key["eden_cinemas"]
    assert eden.adapter_kind_for("https://www.edencinemas.com.mt/special-offers") is AdapterKind.PROMOTION
    assert eden.adapter_kind_for("https://www.edencinemas.com.mt/whats-on") is AdapterKind.EVENT

    visitmalta = by_key["visitmalta_events"]
    assert visitmalta.fetch_mode is FetchMode.BROWSER
    assert visitmalta.minimum_candidates == 1

    spazju = by_key["spazju_kreattiv_events"]
    assert spazju.policy.scope is SourcePolicyScope.POC
    assert spazju.policy.robots_required is True
    assert spazju.policy.allowed_path_prefixes == ("/events/",)
    assert spazju.policy.content_storage_allowed is False

    eurosport = by_key["eurosport_malta_sale"]
    assert eurosport.policy.scope is SourcePolicyScope.POC
    assert eurosport.policy.robots_required is True
    assert eurosport.policy.allowed_path_prefixes == ("/sale",)
    assert eurosport.policy.content_storage_allowed is False


def test_existing_restricted_sources_are_not_relaxed_by_vs06() -> None:
    by_key = {entry.source_key: entry for entry in load_source_catalog()}

    assert by_key["mcdonalds_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["pizzahut_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["franks_malta"].policy.mode is SourceAccessMode.DENY
    assert by_key["wolt_malta"].policy.mode is SourceAccessMode.PARTNER_ONLY
    assert by_key["zara_malta"].policy.mode is SourceAccessMode.PARTNER_ONLY
    assert by_key["cloudigo_malta"].policy.mode is SourceAccessMode.PARTNER_ONLY
    assert by_key["lidl_malta_offers"].policy.scope is SourcePolicyScope.RESEARCH
    assert by_key["eurospin_promotions"].policy.scope is SourcePolicyScope.RESEARCH


def test_custom_catalog_does_not_implicitly_apply_default_vs06_policy_additions(tmp_path: Path) -> None:
    custom = tmp_path / "catalog.json"
    custom.write_text("[]", encoding="utf-8")

    assert load_source_catalog(custom) == ()


def test_hardening_overlay_cannot_change_policy_authority(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.json"
    catalog.write_text(
        """[
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
        ]""",
        encoding="utf-8",
    )
    hardening = tmp_path / "hardening.json"
    hardening.write_text(
        '{"fixture": {"policy": {"mode": "deny"}}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot mutate policy/catalog authority"):
        load_source_catalog(catalog, hardening_path=hardening)
