from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
import os
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from ..domain import SourceAccessMode, SourceObservation, SourcePolicy


META_SOURCE_KEY = "meta_ad_library"
META_POLICY_URL = "https://www.facebook.com/ads/library/api/"
DEFAULT_FIELDS = (
    "id",
    "page_id",
    "page_name",
    "ad_creation_time",
    "ad_creative_bodies",
    "ad_creative_link_captions",
    "ad_creative_link_descriptions",
    "ad_creative_link_titles",
    "ad_delivery_start_time",
    "ad_delivery_stop_time",
    "ad_snapshot_url",
    "publisher_platforms",
    "eu_total_reach",
    "beneficiary_payers",
    "languages",
)


class MetaPublisherPlatform(StrEnum):
    FACEBOOK = "FACEBOOK"
    INSTAGRAM = "INSTAGRAM"


class MetaAdsReadiness(StrEnum):
    DISABLED = "disabled"
    MISSING_DEPENDENCIES = "missing_dependencies"
    READY = "ready"


class MetaAdLibraryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MetaAdsConfig:
    enabled: bool = False
    identity_location_verified: bool = False
    developer_account_ready: bool = False
    platform_policy_accepted: bool = False
    app_id: str | None = None
    api_access_confirmed: bool = False
    access_token: str | None = None
    graph_api_version: str | None = None
    source_policy_approved: bool = False
    reached_countries: tuple[str, ...] = ("MT",)
    publisher_platforms: tuple[MetaPublisherPlatform, ...] = (
        MetaPublisherPlatform.FACEBOOK,
        MetaPublisherPlatform.INSTAGRAM,
    )
    ad_active_status: str = "ACTIVE"
    ad_type: str = "ALL"
    media_type: str = "ALL"
    request_timeout_seconds: float = 20.0
    fields: tuple[str, ...] = DEFAULT_FIELDS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "MetaAdsConfig":
        values = env or os.environ
        platforms = tuple(
            MetaPublisherPlatform(value)
            for value in _csv(values.get("META_AD_LIBRARY_PLATFORMS", "FACEBOOK,INSTAGRAM"))
        )
        countries = tuple(value.upper() for value in _csv(values.get("META_AD_LIBRARY_COUNTRIES", "MT")))
        return cls(
            enabled=_truthy(values.get("META_AD_LIBRARY_ENABLED")),
            identity_location_verified=_truthy(values.get("META_AD_LIBRARY_IDENTITY_LOCATION_VERIFIED")),
            developer_account_ready=_truthy(values.get("META_AD_LIBRARY_DEVELOPER_ACCOUNT_READY")),
            platform_policy_accepted=_truthy(values.get("META_AD_LIBRARY_PLATFORM_POLICY_ACCEPTED")),
            app_id=_clean(values.get("META_AD_LIBRARY_APP_ID")),
            api_access_confirmed=_truthy(values.get("META_AD_LIBRARY_API_ACCESS_CONFIRMED")),
            access_token=_clean(values.get("META_AD_LIBRARY_ACCESS_TOKEN")),
            graph_api_version=_clean(values.get("META_GRAPH_API_VERSION")),
            source_policy_approved=_truthy(values.get("META_AD_LIBRARY_SOURCE_POLICY_APPROVED")),
            reached_countries=countries,
            publisher_platforms=platforms,
            ad_active_status=values.get("META_AD_LIBRARY_ACTIVE_STATUS", "ACTIVE").upper(),
            ad_type=values.get("META_AD_LIBRARY_AD_TYPE", "ALL").upper(),
            media_type=values.get("META_AD_LIBRARY_MEDIA_TYPE", "ALL").upper(),
        )

    @property
    def missing_dependencies(self) -> tuple[str, ...]:
        missing: list[str] = []
        if not self.identity_location_verified:
            missing.append("identity_location_verified")
        if not self.developer_account_ready:
            missing.append("developer_account_ready")
        if not self.platform_policy_accepted:
            missing.append("platform_policy_accepted")
        if not self.app_id:
            missing.append("app_id")
        if not self.api_access_confirmed:
            missing.append("api_access_confirmed")
        if not self.access_token:
            missing.append("access_token")
        if not self.graph_api_version:
            missing.append("graph_api_version")
        if not self.source_policy_approved:
            missing.append("source_policy_approved")
        if not self.reached_countries:
            missing.append("reached_countries")
        if not self.publisher_platforms:
            missing.append("publisher_platforms")
        return tuple(missing)

    @property
    def readiness(self) -> MetaAdsReadiness:
        if not self.enabled:
            return MetaAdsReadiness.DISABLED
        if self.missing_dependencies:
            return MetaAdsReadiness.MISSING_DEPENDENCIES
        return MetaAdsReadiness.READY

    def require_ready(self) -> None:
        if self.readiness is MetaAdsReadiness.READY:
            return
        detail = ", ".join(self.missing_dependencies) or self.readiness.value
        raise MetaAdLibraryError(f"Meta Ad Library is not ready: {detail}")

    def source_policy(self) -> SourcePolicy:
        if not self.source_policy_approved:
            raise MetaAdLibraryError("Meta Ad Library source policy is not approved.")
        return SourcePolicy(
            source_key=META_SOURCE_KEY,
            mode=SourceAccessMode.ALLOW,
            reason="Official Meta Ad Library API access only; no Facebook or Instagram scraping.",
            policy_url=META_POLICY_URL,
            robots_required=False,
        )


@dataclass(frozen=True, slots=True)
class MetaAdRecord:
    library_id: str
    page_id: str | None
    page_name: str | None
    creative_bodies: tuple[str, ...] = ()
    creative_link_captions: tuple[str, ...] = ()
    creative_link_descriptions: tuple[str, ...] = ()
    creative_link_titles: tuple[str, ...] = ()
    creation_time: datetime | None = None
    delivery_start_time: datetime | None = None
    delivery_stop_time: datetime | None = None
    snapshot_url: str | None = None
    publisher_platforms: tuple[str, ...] = ()
    eu_total_reach: int | None = None
    beneficiary_payers: tuple[Mapping[str, Any], ...] = ()
    languages: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "MetaAdRecord":
        return cls(
            library_id=str(payload["id"]),
            page_id=_optional_str(payload.get("page_id")),
            page_name=_optional_str(payload.get("page_name")),
            creative_bodies=_strings(payload.get("ad_creative_bodies")),
            creative_link_captions=_strings(payload.get("ad_creative_link_captions")),
            creative_link_descriptions=_strings(payload.get("ad_creative_link_descriptions")),
            creative_link_titles=_strings(payload.get("ad_creative_link_titles")),
            creation_time=_parse_meta_datetime(payload.get("ad_creation_time")),
            delivery_start_time=_parse_meta_datetime(payload.get("ad_delivery_start_time")),
            delivery_stop_time=_parse_meta_datetime(payload.get("ad_delivery_stop_time")),
            snapshot_url=_sanitize_url(_optional_str(payload.get("ad_snapshot_url"))),
            publisher_platforms=_strings(payload.get("publisher_platforms")),
            eu_total_reach=_optional_int(payload.get("eu_total_reach")),
            beneficiary_payers=tuple(
                value for value in payload.get("beneficiary_payers", []) if isinstance(value, Mapping)
            ),
            languages=_strings(payload.get("languages")),
        )

    def to_observation(self, *, observed_at: datetime) -> SourceObservation:
        extracted = {
            "library_id": self.library_id,
            "page_id": self.page_id,
            "page_name": self.page_name,
            "creative_bodies": self.creative_bodies,
            "creative_link_captions": self.creative_link_captions,
            "creative_link_descriptions": self.creative_link_descriptions,
            "creative_link_titles": self.creative_link_titles,
            "creation_time": _iso(self.creation_time),
            "delivery_start_time": _iso(self.delivery_start_time),
            "delivery_stop_time": _iso(self.delivery_stop_time),
            "snapshot_url": self.snapshot_url,
            "publisher_platforms": self.publisher_platforms,
            "eu_total_reach": self.eu_total_reach,
            "beneficiary_payers": self.beneficiary_payers,
            "languages": self.languages,
        }
        canonical = json.dumps(extracted, sort_keys=True, default=str, separators=(",", ":"))
        return SourceObservation(
            id=uuid4(),
            source_key=META_SOURCE_KEY,
            source_url=self.snapshot_url or f"meta-ad-library://{self.library_id}",
            observed_at=observed_at,
            content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
            extracted=extracted,
            adapter="meta-ad-library-v1",
        )


@dataclass(frozen=True, slots=True)
class MetaAdPage:
    records: tuple[MetaAdRecord, ...]
    after_cursor: str | None = None


JsonTransport = Callable[[str, Mapping[str, str], float], Mapping[str, Any]]


class MetaAdLibraryClient:
    def __init__(self, config: MetaAdsConfig, *, transport: JsonTransport | None = None) -> None:
        self.config = config
        self._transport = transport or _default_transport

    def search(
        self,
        *,
        search_terms: str = "",
        after_cursor: str | None = None,
        delivery_date_min: date | None = None,
        delivery_date_max: date | None = None,
        limit: int = 50,
    ) -> MetaAdPage:
        self.config.require_ready()
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        if delivery_date_min and delivery_date_max and delivery_date_min > delivery_date_max:
            raise ValueError("delivery_date_min cannot be after delivery_date_max")

        params: dict[str, str | int] = {
            "ad_active_status": self.config.ad_active_status,
            "ad_type": self.config.ad_type,
            "media_type": self.config.media_type,
            "ad_reached_countries": json.dumps(self.config.reached_countries, separators=(",", ":")),
            "publisher_platforms": json.dumps(
                tuple(platform.value for platform in self.config.publisher_platforms), separators=(",", ":")
            ),
            "fields": ",".join(self.config.fields),
            "limit": limit,
        }
        if search_terms:
            params["search_terms"] = search_terms[:100]
        if after_cursor:
            params["after"] = after_cursor
        if delivery_date_min:
            params["ad_delivery_date_min"] = delivery_date_min.isoformat()
        if delivery_date_max:
            params["ad_delivery_date_max"] = delivery_date_max.isoformat()

        url = f"https://graph.facebook.com/{self.config.graph_api_version}/ads_archive?{urlencode(params)}"
        payload = self._transport(
            url,
            {"Authorization": f"Bearer {self.config.access_token}", "Accept": "application/json"},
            self.config.request_timeout_seconds,
        )
        if "error" in payload:
            error = payload.get("error")
            message = error.get("message") if isinstance(error, Mapping) else str(error)
            raise MetaAdLibraryError(f"Meta Ad Library API error: {message}")

        records = tuple(
            MetaAdRecord.from_payload(item)
            for item in payload.get("data", [])
            if isinstance(item, Mapping) and item.get("id") is not None
        )
        paging = payload.get("paging") if isinstance(payload.get("paging"), Mapping) else {}
        cursors = paging.get("cursors") if isinstance(paging.get("cursors"), Mapping) else {}
        after = _optional_str(cursors.get("after"))
        return MetaAdPage(records=records, after_cursor=after)


def _default_transport(url: str, headers: Mapping[str, str], timeout: float) -> Mapping[str, Any]:
    request = Request(url, headers=dict(headers), method="GET")
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS Meta endpoint
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise MetaAdLibraryError("Meta Ad Library returned a non-object JSON payload.")
    return payload


def _sanitize_url(value: str | None) -> str | None:
    if not value:
        return None
    split = urlsplit(value)
    query = [(key, item) for key, item in parse_qsl(split.query, keep_blank_values=True) if key != "access_token"]
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


def _parse_meta_datetime(value: object) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _truthy(value: str | None) -> bool:
    return (value or "").strip().casefold() in {"1", "true", "yes", "on"}


def _clean(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _strings(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, Sequence):
        return tuple(str(item) for item in value if item is not None)
    return (str(value),)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
