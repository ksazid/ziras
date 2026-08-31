from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import json
from pathlib import Path
from typing import Iterable, Mapping
from urllib.parse import urlsplit

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
    route_adapter_kinds: tuple[tuple[str, AdapterKind], ...] = ()
    minimum_candidates: int = 0

    def adapter_kind_for(self, source_url: str) -> AdapterKind:
        path = urlsplit(source_url).path or "/"
        matches = (
            (prefix, kind)
            for prefix, kind in self.route_adapter_kinds
            if path.startswith(prefix)
        )
        best = max(matches, key=lambda item: len(item[0]), default=None)
        return best[1] if best else self.adapter_kind


def default_malta_catalog_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "malta-source-policy.json"


def default_malta_poc_extension_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "malta-source-vs06-poc.json"


def default_malta_household_poc_extension_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "malta-source-vs07-poc.json"


def default_malta_hardening_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "malta-source-hardening.json"


def load_source_catalog(
    path: str | Path | None = None,
    *,
    extension_path: str | Path | None = None,
    hardening_path: str | Path | None = None,
) -> tuple[SourceCatalogEntry, ...]:
    catalog_path = Path(path) if path is not None else default_malta_catalog_path()
    payload = _read_json(catalog_path)
    if not isinstance(payload, list):
        raise ValueError("source catalog must be a JSON array")

    resolved_extensions: tuple[Path, ...] = ()
    if extension_path is not None:
        resolved_extensions = (Path(extension_path),)
    elif path is None:
        resolved_extensions = (
            default_malta_poc_extension_path(),
            default_malta_household_poc_extension_path(),
        )

    for resolved_extension in resolved_extensions:
        if not resolved_extension.exists():
            continue
        extension = _read_json(resolved_extension)
        if not isinstance(extension, list):
            raise ValueError("source catalog extension must be a JSON array")
        payload = [*payload, *extension]

    overrides: Mapping[str, object] = {}
    resolved_hardening: Path | None = None
    if path is None or hardening_path is not None:
        resolved_hardening = (
            Path(hardening_path) if hardening_path is not None else default_malta_hardening_path()
        )

    if resolved_hardening is not None and resolved_hardening.exists():
        raw_overrides = _read_json(resolved_hardening)
        if not isinstance(raw_overrides, dict):
            raise ValueError("source hardening file must be a JSON object keyed by source_key")
        overrides = raw_overrides

    entries: list[SourceCatalogEntry] = []
    seen: set[str] = set()
    for raw in payload:
        entry = _entry_from_raw(raw, overrides=overrides)
        if entry.source_key in seen:
            raise ValueError(f"duplicate source_key: {entry.source_key}")
        seen.add(entry.source_key)
        entries.append(entry)

    unknown_overrides = sorted(set(overrides) - seen)
    if unknown_overrides:
        raise ValueError(f"source hardening references unknown source: {unknown_overrides[0]}")

    return tuple(entries)


def build_policy_registry(entries: Iterable[SourceCatalogEntry]) -> SourcePolicyRegistry:
    return SourcePolicyRegistry({entry.source_key: entry.policy for entry in entries})


def _entry_from_raw(raw: object, *, overrides: Mapping[str, object]) -> SourceCatalogEntry:
    if not isinstance(raw, dict):
        raise ValueError("source catalog entry must be an object")
    source_key = str(raw["source_key"])
    policy_raw = raw["policy"]
    if not isinstance(policy_raw, dict):
        raise ValueError(f"policy must be an object for {source_key}")
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

    override = overrides.get(source_key, {})
    if not isinstance(override, dict):
        raise ValueError(f"source hardening override must be an object for {source_key}")
    forbidden = set(override) - {"route_adapter_kinds", "minimum_candidates"}
    if forbidden:
        raise ValueError(
            f"source hardening cannot mutate policy/catalog authority for {source_key}: {sorted(forbidden)}"
        )

    route_raw = override.get("route_adapter_kinds", raw.get("route_adapter_kinds", {}))
    if not isinstance(route_raw, dict):
        raise ValueError(f"route_adapter_kinds must be an object for {source_key}")
    route_adapter_kinds = tuple(
        (str(prefix), AdapterKind(kind)) for prefix, kind in route_raw.items()
    )
    minimum_candidates = int(
        override.get("minimum_candidates", raw.get("minimum_candidates", 0))
    )
    if minimum_candidates < 0:
        raise ValueError(f"minimum_candidates must be >= 0 for {source_key}")

    return SourceCatalogEntry(
        source_key=source_key,
        display_name=str(raw["display_name"]),
        source_class=str(raw["source_class"]),
        start_urls=tuple(str(url) for url in raw.get("start_urls", ())),
        fetch_mode=FetchMode(raw["fetch_mode"]),
        adapter_kind=AdapterKind(raw["adapter_kind"]),
        policy=policy,
        terms_url=raw.get("terms_url"),
        notes=raw.get("notes"),
        route_adapter_kinds=route_adapter_kinds,
        minimum_candidates=minimum_candidates,
    )


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))
