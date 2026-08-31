from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Mapping
from urllib.parse import urlsplit

from ..domain import Discovery, DiscoveryType, SourceAccessMode, SourcePolicy
from ..policy import SourcePolicyRegistry
from ..ports import SourceAdapterResult
from .structured_html import StructuredHtmlAdapter


class SourcePackError(RuntimeError):
    pass


class SourceKind(StrEnum):
    EVENTS = "events"
    DEALS = "deals"
    RETAIL = "retail"
    RESTAURANT = "restaurant"


class PolicyStage(StrEnum):
    REVIEW_REQUIRED = "review_required"
    PARTNER_REQUIRED = "partner_required"
    APPROVED = "approved"
    PROHIBITED = "prohibited"


@dataclass(frozen=True, slots=True)
class SourceProfile:
    source_key: str
    display_name: str
    domains: tuple[str, ...]
    kind: SourceKind
    entry_urls: tuple[str, ...]
    policy_stage: PolicyStage
    robots_required: bool = True
    browser_fallback_allowed: bool = True
    policy_url: str | None = None
    notes: str | None = None

    def accepts_url(self, url: str) -> bool:
        split = urlsplit(url)
        if split.scheme != "https":
            return False
        host = (split.hostname or "").casefold()
        return any(host == domain or host.endswith(f".{domain}") for domain in self.domains)


@dataclass(frozen=True, slots=True)
class SourcePackReadiness:
    source_key: str
    allowed: bool
    mode: SourceAccessMode
    reason: str
    policy_stage: PolicyStage
    entry_urls: tuple[str, ...]
    browser_fallback_allowed: bool


SOURCE_PROFILES: Mapping[str, SourceProfile] = {
    "visitmalta_events": SourceProfile(
        source_key="visitmalta_events",
        display_name="VisitMalta Events",
        domains=("visitmalta.com",),
        kind=SourceKind.EVENTS,
        entry_urls=("https://www.visitmalta.com/en/events-in-malta-and-gozo/",),
        policy_stage=PolicyStage.REVIEW_REQUIRED,
        robots_required=True,
        browser_fallback_allowed=True,
        policy_url="https://www.visitmalta.com/en/terms-and-conditions/",
        notes="Official Malta Tourism Authority event inventory. Public pages and sitemap are useful discovery signals; automated collection remains disabled until policy/robots review is approved.",
    ),
    "deal_mt": SourceProfile(
        source_key="deal_mt",
        display_name="Deal.com.mt",
        domains=("deal.com.mt",),
        kind=SourceKind.DEALS,
        entry_urls=("https://deal.com.mt/",),
        policy_stage=PolicyStage.PARTNER_REQUIRED,
        robots_required=True,
        browser_fallback_allowed=True,
        notes="High-density Malta deal inventory. Keep partner-only until explicit automated-access permission or partner feed/API is established.",
    ),
    "scan_malta": SourceProfile(
        source_key="scan_malta",
        display_name="SCAN Malta",
        domains=("scanmalta.com",),
        kind=SourceKind.RETAIL,
        entry_urls=("https://www.scanmalta.com/",),
        policy_stage=PolicyStage.REVIEW_REQUIRED,
        robots_required=True,
        browser_fallback_allowed=True,
        notes="Retail product and special-price candidate. Production collection requires source-policy review.",
    ),
    "greens_malta": SourceProfile(
        source_key="greens_malta",
        display_name="Greens Supermarket",
        domains=("greens.com.mt",),
        kind=SourceKind.RETAIL,
        entry_urls=("https://www.greens.com.mt/",),
        policy_stage=PolicyStage.REVIEW_REQUIRED,
        robots_required=True,
        browser_fallback_allowed=True,
        notes="Supermarket/ecommerce candidate for price and promotion discovery. Production collection requires source-policy review.",
    ),
    "decathlon_malta": SourceProfile(
        source_key="decathlon_malta",
        display_name="Decathlon Malta",
        domains=("decathlon.mt",),
        kind=SourceKind.RETAIL,
        entry_urls=("https://www.decathlon.mt/",),
        policy_stage=PolicyStage.REVIEW_REQUIRED,
        robots_required=True,
        browser_fallback_allowed=True,
        notes="Retail product/price-drop candidate. Production collection requires source-policy review.",
    ),
    "atrium_malta": SourceProfile(
        source_key="atrium_malta",
        display_name="The Atrium Malta",
        domains=("atrium.com.mt",),
        kind=SourceKind.RETAIL,
        entry_urls=("https://www.atrium.com.mt/",),
        policy_stage=PolicyStage.REVIEW_REQUIRED,
        robots_required=True,
        browser_fallback_allowed=True,
        notes="Home/lifestyle retail candidate. Production collection requires source-policy review.",
    ),
    "pizza_hut_malta": SourceProfile(
        source_key="pizza_hut_malta",
        display_name="Pizza Hut Malta",
        domains=("pizzahut.com.mt",),
        kind=SourceKind.RESTAURANT,
        entry_urls=("https://www.pizzahut.com.mt/",),
        policy_stage=PolicyStage.REVIEW_REQUIRED,
        robots_required=True,
        browser_fallback_allowed=True,
        notes="Restaurant/menu/promotion candidate. Production collection requires source-policy review.",
    ),
    "shows_happening": SourceProfile(
        source_key="shows_happening",
        display_name="ShowsHappening",
        domains=("showshappening.com",),
        kind=SourceKind.EVENTS,
        entry_urls=("https://www.showshappening.com/",),
        policy_stage=PolicyStage.PARTNER_REQUIRED,
        robots_required=True,
        browser_fallback_allowed=True,
        notes="Ticketing/event candidate. Prefer partner/API/feed access rather than unapproved automated extraction.",
    ),
}


class SourcePackAdapter:
    """Policy-gated, declarative adapter for the first Malta source pack.

    This layer deliberately does not fetch pages itself. Acquisition remains behind
    the Scrapy/Playwright ports from ADR-001. The adapter only accepts HTML after
    SourcePolicy has explicitly allowed collection for the source key.
    """

    name = "source-pack-v1"

    def __init__(
        self,
        policy_registry: SourcePolicyRegistry,
        *,
        profiles: Mapping[str, SourceProfile] | None = None,
    ) -> None:
        self._policy_registry = policy_registry
        self._profiles = dict(profiles or SOURCE_PROFILES)
        self._structured = StructuredHtmlAdapter()

    def profile(self, source_key: str) -> SourceProfile:
        try:
            return self._profiles[source_key]
        except KeyError as exc:
            raise SourcePackError(f"Unknown source profile: {source_key}") from exc

    def readiness(self, source_key: str, *, partner: bool = False) -> SourcePackReadiness:
        profile = self.profile(source_key)
        decision = self._policy_registry.decide(source_key, partner=partner)
        return SourcePackReadiness(
            source_key=source_key,
            allowed=decision.allowed,
            mode=decision.mode,
            reason=decision.reason,
            policy_stage=profile.policy_stage,
            entry_urls=profile.entry_urls,
            browser_fallback_allowed=profile.browser_fallback_allowed,
        )

    def extract(
        self,
        *,
        source_key: str,
        source_url: str,
        html: str,
        observed_at: datetime,
        content_hash: str,
        partner: bool = False,
    ) -> SourceAdapterResult:
        profile = self.profile(source_key)
        if not profile.accepts_url(source_url):
            raise SourcePackError(f"Source URL is outside the approved domain set for {source_key}.")

        decision = self._policy_registry.decide(source_key, partner=partner)
        if not decision.allowed:
            raise SourcePackError(f"Source policy denied {source_key}: {decision.reason}")

        result = self._structured.extract(
            source_key=source_key,
            source_url=source_url,
            html=html,
            observed_at=observed_at,
            content_hash=content_hash,
        )
        discoveries = self._normalize(profile, result.discoveries)
        observation = replace(
            result.observation,
            adapter=self.name,
            extracted={
                **result.observation.extracted,
                "source_profile": profile.source_key,
                "source_kind": profile.kind.value,
                "policy_mode": decision.mode.value,
            },
        )
        return SourceAdapterResult(observation=observation, discoveries=discoveries)

    def _normalize(self, profile: SourceProfile, discoveries: tuple[Discovery, ...]) -> tuple[Discovery, ...]:
        normalized: list[Discovery] = []
        seen: set[tuple[object, ...]] = set()
        for discovery in discoveries:
            discovery_type = discovery.discovery_type
            if profile.kind is SourceKind.EVENTS:
                discovery_type = DiscoveryType.EVENT
            elif profile.kind is SourceKind.DEALS:
                discovery_type = DiscoveryType.DEAL

            current = replace(discovery, discovery_type=discovery_type)
            key = (
                current.discovery_type,
                current.title.casefold().strip(),
                current.current_price,
                current.currency,
                current.starts_at,
                current.expires_at,
            )
            if key in seen:
                continue
            seen.add(key)
            normalized.append(current)
        return tuple(normalized)


def candidate_policy_registry() -> SourcePolicyRegistry:
    """Create the safe default registry for VS-04.

    Review-required sources are DENY. Partner-required sources are PARTNER_ONLY.
    No source in the production pack is automatically allowed by this function.
    """

    policies: dict[str, SourcePolicy] = {}
    for profile in SOURCE_PROFILES.values():
        if profile.policy_stage is PolicyStage.PARTNER_REQUIRED:
            mode = SourceAccessMode.PARTNER_ONLY
            reason = "Partner/API/feed permission required before automated collection."
        elif profile.policy_stage is PolicyStage.PROHIBITED:
            mode = SourceAccessMode.DENY
            reason = "Automated collection is prohibited for this source."
        elif profile.policy_stage is PolicyStage.APPROVED:
            mode = SourceAccessMode.ALLOW
            reason = "Source policy has been explicitly approved."
        else:
            mode = SourceAccessMode.DENY
            reason = "Source-policy and robots review required before automated collection."
        policies[profile.source_key] = SourcePolicy(
            source_key=profile.source_key,
            mode=mode,
            reason=reason,
            policy_url=profile.policy_url,
            robots_required=profile.robots_required,
        )
    return SourcePolicyRegistry(policies)
