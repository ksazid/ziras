from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import json
from pathlib import Path
from typing import Iterable

from .domain import SourceAccessMode, SourcePolicy, SourcePolicyScope
from .policy import SourcePolicyRegistry


class FetchMode(StrEnum):
    STATIC = "static"
    BROWSER = "browser"
    API = "api"
    USER_SHARE = "user_share"


class AdapterKind(StrEnum):
    STRUCTURED = "structured"
    PROMOTION = "promotion"
    EVENT = "event"
    META_AD_LIBRARY = "meta_ad_library"


@dataclass(frozen=True, slots=True)
class SourceCatalogEntry:
    source_key: str
    display_name: str
    source_class: str
    start_urls: tuple[str, ...]
    fetch_mode: FetchMode
    adapter_kind: AdapterKind
    policy: SourcePolicy
    terms_url: str | None = None
    notes: str | None = None


def default_malta_catalog_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "malta-source-policy.json"


def load_source_catalog(path: str | Path | None = None) -> tuple[SourceCatalogEntry, ...]:
    catalog_path = Path(path) if path is not None else default_malta_catalog_path()
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("source catalog must be a JSON array")

    entries: list[SourceCatalogEntry] = []
    seen: set[str] = set()
    for raw in payload:
        source_key = str(raw["source_key"])
        if source_key in seen:
            raise ValueError(f"duplicate source_key: {source_key}")
        seen.add(source_key)

        policy_raw = raw["policy"]
        reviewed_at = (
            datetime.fromisoformat(policy_raw["reviewed_at"])
            if policy_raw.get("reviewed_at")
            else None
        )
        policy = SourcePolicy(
            source_key=source_key,
            mode=SourceAccessMode(policy_raw["mode"]),
            reason=str(policy_raw["reason"]),
            policy_url=policy_raw.get("policy_url"),
            robots_required=bool(policy_raw.get("robots_required", True)),
            reviewed_at=reviewed_at,
            scope=SourcePolicyScope(policy_raw.get("scope", "production")),
            allowed_path_prefixes=tuple(policy_raw.get("allowed_path_prefixes", ())),
            max_requests_per_hour=int(policy_raw.get("max_requests_per_hour", 1)),
            attribution_required=bool(policy_raw.get("attribution_required", True)),
            content_storage_allowed=bool(policy_raw.get("content_storage_allowed", False)),
        )
        entries.append(
            SourceCatalogEntry(
                source_key=source_key,
                display_name=str(raw["display_name"]),
                source_class=str(raw["source_class"]),
                start_urls=tuple(str(url) for url in raw.get("start_urls", ())),
                fetch_mode=FetchMode(raw["fetch_mode"]),
                adapter_kind=AdapterKind(raw["adapter_kind"]),
                policy=policy,
                terms_url=raw.get("terms_url"),
                notes=raw.get("notes"),
            )
        )
    return tuple(entries)


def build_policy_registry(entries: Iterable[SourceCatalogEntry]) -> SourcePolicyRegistry:
    return SourcePolicyRegistry({entry.source_key: entry.policy for entry in entries})
