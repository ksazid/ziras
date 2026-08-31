from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .domain import SourceAccessMode, SourcePolicy


@dataclass(frozen=True, slots=True)
class SourcePolicyDecision:
    allowed: bool
    mode: SourceAccessMode
    reason: str
    policy: SourcePolicy | None


class SourcePolicyRegistry:
    """Fail-closed policy registry. Unknown sources are denied."""

    def __init__(self, policies: Mapping[str, SourcePolicy] | None = None) -> None:
        self._policies = dict(policies or {})

    def register(self, policy: SourcePolicy) -> None:
        self._policies[policy.source_key] = policy

    def decide(self, source_key: str, *, user_shared: bool = False, partner: bool = False) -> SourcePolicyDecision:
        policy = self._policies.get(source_key)
        if policy is None:
            return SourcePolicyDecision(
                allowed=False,
                mode=SourceAccessMode.DENY,
                reason="Source has no approved policy record.",
                policy=None,
            )

        if policy.mode is SourceAccessMode.DENY:
            return SourcePolicyDecision(False, policy.mode, policy.reason, policy)
        if policy.mode is SourceAccessMode.PARTNER_ONLY and not partner:
            return SourcePolicyDecision(False, policy.mode, "Partner access required.", policy)
        if policy.mode is SourceAccessMode.USER_SHARE_ONLY and not user_shared:
            return SourcePolicyDecision(False, policy.mode, "User-shared ingestion required.", policy)
        return SourcePolicyDecision(True, policy.mode, policy.reason, policy)
