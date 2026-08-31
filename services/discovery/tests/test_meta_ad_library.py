from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import pytest

from ziras_discovery.adapters.meta_ad_library import (
    META_SOURCE_KEY,
    MetaAdLibraryClient,
    MetaAdLibraryError,
    MetaAdsConfig,
    MetaAdsReadiness,
    MetaPublisherPlatform,
)


NOW = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)


def _ready_config(**overrides: object) -> MetaAdsConfig:
    values: dict[str, object] = {
        "enabled": True,
        "identity_location_verified": True,
        "developer_account_ready": True,
        "platform_policy_accepted": True,
        "app_id": "123456789",
        "api_access_confirmed": True,
        "access_token": "secret-token",
        "graph_api_version": "v-test",
        "source_policy_approved": True,
        "reached_countries": ("MT",),
        "publisher_platforms": (
            MetaPublisherPlatform.FACEBOOK,
            MetaPublisherPlatform.INSTAGRAM,
        ),
    }
    values.update(overrides)
    return MetaAdsConfig(**values)


def test_meta_is_disabled_by_default() -> None:
    config = MetaAdsConfig()
    assert config.readiness is MetaAdsReadiness.DISABLED
    with pytest.raises(MetaAdLibraryError):
        config.require_ready()


def test_meta_tracks_every_enablement_dependency() -> None:
    config = MetaAdsConfig(enabled=True, reached_countries=(), publisher_platforms=())
    assert config.readiness is MetaAdsReadiness.MISSING_DEPENDENCIES
    assert set(config.missing_dependencies) == {
        "identity_location_verified",
        "developer_account_ready",
        "platform_policy_accepted",
        "app_id",
        "api_access_confirmed",
        "access_token",
        "graph_api_version",
        "source_policy_approved",
        "reached_countries",
        "publisher_platforms",
    }


def test_env_configuration_enables_facebook_and_instagram_for_malta() -> None:
    config = MetaAdsConfig.from_env(
        {
            "META_AD_LIBRARY_ENABLED": "true",
            "META_AD_LIBRARY_IDENTITY_LOCATION_VERIFIED": "true",
            "META_AD_LIBRARY_DEVELOPER_ACCOUNT_READY": "true",
            "META_AD_LIBRARY_PLATFORM_POLICY_ACCEPTED": "true",
            "META_AD_LIBRARY_APP_ID": "123",
            "META_AD_LIBRARY_API_ACCESS_CONFIRMED": "true",
            "META_AD_LIBRARY_ACCESS_TOKEN": "token",
            "META_GRAPH_API_VERSION": "v-test",
            "META_AD_LIBRARY_SOURCE_POLICY_APPROVED": "true",
            "META_AD_LIBRARY_COUNTRIES": "MT",
            "META_AD_LIBRARY_PLATFORMS": "FACEBOOK,INSTAGRAM",
        }
    )
    assert config.readiness is MetaAdsReadiness.READY
    assert config.reached_countries == ("MT",)
    assert config.publisher_platforms == (
        MetaPublisherPlatform.FACEBOOK,
        MetaPublisherPlatform.INSTAGRAM,
    )
    assert config.source_policy().source_key == META_SOURCE_KEY


def test_search_uses_official_api_filters_and_does_not_put_token_in_url() -> None:
    captured: dict[str, object] = {}

    def transport(url: str, headers: dict[str, str], timeout: float) -> dict[str, object]:
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {
            "data": [
                {
                    "id": "987",
                    "page_id": "456",
                    "page_name": "Example Malta",
                    "ad_creative_bodies": ["Weekend special offer"],
                    "ad_delivery_start_time": "2026-08-30T10:00:00+0000",
                    "ad_snapshot_url": "https://www.facebook.com/ads/archive/render_ad/?id=987&access_token=leak-me",
                    "publisher_platforms": ["FACEBOOK", "INSTAGRAM"],
                    "eu_total_reach": 1200,
                }
            ],
            "paging": {"cursors": {"after": "next-cursor"}},
        }

    client = MetaAdLibraryClient(_ready_config(), transport=transport)
    page = client.search(search_terms="weekend offer")

    url = str(captured["url"])
    assert "secret-token" not in url
    query = parse_qs(urlsplit(url).query)
    assert query["ad_reached_countries"] == ['["MT"]']
    assert query["publisher_platforms"] == ['["FACEBOOK","INSTAGRAM"]']
    assert query["ad_type"] == ["ALL"]
    assert query["ad_active_status"] == ["ACTIVE"]
    assert query["search_terms"] == ["weekend offer"]
    assert captured["headers"] == {
        "Authorization": "Bearer secret-token",
        "Accept": "application/json",
    }

    assert page.after_cursor == "next-cursor"
    assert len(page.records) == 1
    record = page.records[0]
    assert record.library_id == "987"
    assert record.publisher_platforms == ("FACEBOOK", "INSTAGRAM")
    assert "access_token" not in (record.snapshot_url or "")

    observation = record.to_observation(observed_at=NOW)
    assert observation.source_key == META_SOURCE_KEY
    assert observation.adapter == "meta-ad-library-v1"
    assert "access_token" not in observation.source_url
    assert "secret-token" not in str(observation.extracted)


def test_source_policy_cannot_be_created_without_explicit_policy_approval() -> None:
    config = _ready_config(source_policy_approved=False)
    with pytest.raises(MetaAdLibraryError):
        config.source_policy()
