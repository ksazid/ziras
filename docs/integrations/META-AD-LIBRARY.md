# Meta Ad Library integration

Status: implemented but disabled by default.

Ziras uses the official Meta Ad Library API only. This integration does **not** authorize scraping Facebook or Instagram pages.

## Product purpose

Use public Meta ad observations as evidence for local discoveries. An ad is an observation, not automatically a deal. The normal Ziras normalization/freshness pipeline decides whether the ad supports a `DEAL`, `OPENING`, `EVENT`, `NEW_PRODUCT`, `NEW_MENU`, or another discovery type.

Malta-first default:

- reached country: `MT`
- publisher platforms: `FACEBOOK`, `INSTAGRAM`
- active status: `ACTIVE`
- ad type: `ALL`
- media type: `ALL`

## External prerequisites

Before enabling the adapter, complete all of the following:

1. Facebook account available for the operator responsible for API access.
2. Meta identity/location confirmation completed where required by the Ad Library API onboarding flow.
3. Meta for Developers account created.
4. Meta Platform Policy accepted.
5. Meta developer app created; record the app ID.
6. Ad Library API access confirmed for that app/account.
7. Valid access token created and stored only in deployment secret storage.
8. Current supported Meta Graph API version selected and pinned in deployment configuration.
9. Ziras SourcePolicy review approved for `meta_ad_library`.
10. Desired countries and publisher platforms explicitly configured.

These prerequisites are represented in `MetaAdsConfig.missing_dependencies`; the adapter refuses to run until all are satisfied and `META_AD_LIBRARY_ENABLED=true`.

## Runtime configuration

Copy the names from `services/discovery/config/meta-ad-library.env.example` into the deployment environment. Do not commit the access token.

Required readiness variables:

- `META_AD_LIBRARY_ENABLED`
- `META_AD_LIBRARY_IDENTITY_LOCATION_VERIFIED`
- `META_AD_LIBRARY_DEVELOPER_ACCOUNT_READY`
- `META_AD_LIBRARY_PLATFORM_POLICY_ACCEPTED`
- `META_AD_LIBRARY_APP_ID`
- `META_AD_LIBRARY_API_ACCESS_CONFIRMED`
- `META_AD_LIBRARY_ACCESS_TOKEN` (secret)
- `META_GRAPH_API_VERSION`
- `META_AD_LIBRARY_SOURCE_POLICY_APPROVED`
- `META_AD_LIBRARY_COUNTRIES`
- `META_AD_LIBRARY_PLATFORMS`

Optional query defaults:

- `META_AD_LIBRARY_ACTIVE_STATUS=ACTIVE`
- `META_AD_LIBRARY_AD_TYPE=ALL`
- `META_AD_LIBRARY_MEDIA_TYPE=ALL`

`MetaAdLibraryClient.search()` also accepts `delivery_date_min` and `delivery_date_max`, allowing the collector to query a bounded historical window without changing global configuration.

## Readiness states

- `disabled`: capability intentionally off.
- `missing_dependencies`: one or more prerequisites are incomplete; inspect `missing_dependencies`.
- `ready`: all runtime and governance dependencies are present.

Runtime API failures are surfaced as `MetaAdLibraryError` and must be observed separately from configuration readiness.

## Data acquired

The adapter requests supported Ad Library fields including:

- library ad ID
- advertiser Page ID/name
- creative body/link text
- creation/delivery dates
- archived ad snapshot URL
- publisher platforms (Facebook/Instagram etc.)
- EU reach when returned by Meta
- EU beneficiary/payer data when returned by Meta
- languages

The access token is sent as an Authorization header and is never intentionally persisted in `SourceObservation`. Snapshot URLs are sanitized to remove an `access_token` query parameter before storage.

## Query behavior

The official endpoint is:

`https://graph.facebook.com/<META_GRAPH_API_VERSION>/ads_archive`

Ziras supports the core official filters needed for discovery collection:

- reached country
- Facebook/Instagram publisher platform
- active/inactive/all delivery state
- ad type
- media type
- delivery date min/max
- search terms
- cursor pagination

Pagination stores only the `after` cursor; it does not persist Meta's raw `paging.next` URL because that URL may contain credentials.

## Operational checks before production enablement

- readiness == `ready`
- a smoke query for `MT` succeeds
- returned records include expected Facebook/Instagram publisher platform values
- current and bounded historical date queries work as expected
- image/video media filtering works as expected when configured
- no token appears in logs, source URLs, observation JSON, errors, or metrics
- rate-limit/error telemetry is visible
- token rotation procedure is documented for the deployment environment
- source policy remains approved and current
- Meta terms/API behavior are re-reviewed before production enablement

## Current scope

VS-03 adds the integration boundary, configuration/readiness tracking, official API client, normalization into source observations, and deterministic tests. It does not enable production credentials or production collection.
