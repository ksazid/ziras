from __future__ import annotations

import json

import pytest

from ziras_discovery.domain import SourceAccessMode, SourcePolicyScope
from ziras_discovery.source_catalog import FetchMode, load_source_catalog


def test_vs06_dynamic_sources_use_browser_without_relaxing_policy() -> None:
    by_key = {entry.source_key: entry for entry in load_source_catalog()}

    for source_key in ("visitmalta_events", "eden_cinemas", "eurosport_malta_sale"):
        entry = by_key[source_key]
        assert entry.fetch_mode is FetchMode.BROWSER
        assert entry.policy.mode is SourceAccessMode.ALLOW
        assert entry.policy.scope is SourcePolicyScope.POC

    for source_key in (
        "visitmalta_events",
        "eden_cinemas",
        "homemate_offers",
        "spazju_kreattiv_events",
        "eurosport_malta_sale",
    ):
        assert by_key[source_key].minimum_candidates >= 1


def test_hardening_can_change_fetch_mode_but_not_policy(tmp_path) -> None:
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
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    hardening.write_text(
        json.dumps({"fixture": {"fetch_mode": "browser", "minimum_candidates": 1}}),
        encoding="utf-8",
    )

    entry = load_source_catalog(catalog, hardening_path=hardening)[0]
    assert entry.fetch_mode is FetchMode.BROWSER
    assert entry.minimum_candidates == 1
    assert entry.policy.mode is SourceAccessMode.ALLOW

    hardening.write_text(
        json.dumps({"fixture": {"policy": {"mode": "deny"}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="cannot mutate policy/catalog authority"):
        load_source_catalog(catalog, hardening_path=hardening)
