from __future__ import annotations

from ziras_discovery.domain import SourceAccessMode, SourcePolicyScope
from ziras_discovery.source_catalog import load_source_catalog


def test_ax_noisy_sources_are_quarantined_and_poc_only() -> None:
    entries = {entry.source_key: entry for entry in load_source_catalog()}

    sliema = entries["ax_sliema_dining_offers"]
    assert sliema.start_urls == ()
    assert sliema.policy.max_requests_per_hour == 1
    assert sliema.policy.mode is SourceAccessMode.ALLOW
    assert sliema.policy.scope is SourcePolicyScope.POC

    verdala = entries["ax_verdala_wellness_offers"]
    assert verdala.start_urls == ()
    assert verdala.policy.mode is SourceAccessMode.ALLOW
    assert verdala.policy.scope is SourcePolicyScope.POC


def test_ax_quarantine_does_not_enable_production_access() -> None:
    entries = {entry.source_key: entry for entry in load_source_catalog()}

    assert entries["ax_sliema_dining_offers"].policy.scope is SourcePolicyScope.POC
    assert entries["ax_verdala_wellness_offers"].policy.scope is SourcePolicyScope.POC
