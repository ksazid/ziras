from __future__ import annotations

import json
from pathlib import Path

from ziras_discovery.domain import SourceAccessMode, SourcePolicyScope
from ziras_discovery.source_catalog import AdapterKind, load_source_catalog


QUARANTINED = {
    "eden_cinemas",
    "eden_cinemas_coming_soon",
    "lidl_malta_poc_offers",
    "heritage_malta_activities",
    "active_ageing_discounts",
    "botika_personal_care_sale",
    "ax_sliema_dining_offers",
    "ax_verdala_wellness_offers",
}


def test_day2_unhealthy_sources_are_fail_closed_without_changing_policy() -> None:
    entries = {entry.source_key: entry for entry in load_source_catalog()}

    for key in QUARANTINED:
        entry = entries[key]
        assert entry.start_urls == ()
        assert entry.policy.mode is SourceAccessMode.ALLOW
        assert entry.policy.scope is SourcePolicyScope.POC
        assert entry.policy.content_storage_allowed is False


def test_eden_replacement_remains_defined_but_is_quarantined_after_unhealthy_evidence() -> None:
    entry = next(item for item in load_source_catalog() if item.source_key == "eden_cinemas_coming_soon")

    assert entry.start_urls == ()
    assert entry.adapter_kind is AdapterKind.EVENT
    assert entry.minimum_candidates == 1
    assert entry.policy.scope is SourcePolicyScope.POC
    assert entry.policy.allowed_path_prefixes == ("/coming-soon",)
    assert entry.policy.max_requests_per_hour == 1
    assert entry.policy.content_storage_allowed is False


def test_active_poc_inventory_keeps_exact_five_independent_source_classes() -> None:
    active = [
        entry
        for entry in load_source_catalog()
        if entry.start_urls
        and entry.policy.mode is SourceAccessMode.ALLOW
        and entry.policy.scope is SourcePolicyScope.POC
    ]

    assert {entry.source_class for entry in active} == {
        "events-official",
        "home-retail",
        "cultural-venue-events",
        "sports-retail",
        "family-kids",
    }


def test_disabled_hardening_only_removes_requests_and_cannot_broaden_policy(tmp_path: Path) -> None:
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
                        "allowed_path_prefixes": ["/offers"],
                        "content_storage_allowed": False,
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    hardening.write_text('{"fixture": {"disabled": true}}', encoding="utf-8")

    entry = load_source_catalog(catalog, hardening_path=hardening)[0]

    assert entry.start_urls == ()
    assert entry.policy.mode is SourceAccessMode.ALLOW
    assert entry.policy.scope is SourcePolicyScope.POC
    assert entry.policy.allowed_path_prefixes == ("/offers",)
    assert entry.policy.content_storage_allowed is False
