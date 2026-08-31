# Technical Requirements Document

Status: Draft

## Architecture

The Ziras discovery-engine architecture baseline is **approved** by `ADR-001 — Ziras Discovery Engine Architecture` and `DEC-01`.

Approved discovery-engine direction:

- Python 3.12 modular-monolith discovery kernel.
- Static-first acquisition with Scrapy `2.18.0`.
- `scrapy-playwright==0.0.48` only as browser-rendering fallback.
- Deterministic extraction before AI using structured metadata, source adapters, Trafilatura, price-parser and Dateparser.
- PostgreSQL 16 as the primary data backbone.
- PostGIS for geospatial queries.
- pgvector for semantic interest/discovery similarity.
- PostgresHuey `3.3.4` for MVP background jobs/scheduling; Redis is not required for MVP.
- Photon behind a replaceable `Geocoder` boundary.
- Deterministic/explainable MVP ranking; `implicit` is deferred until sufficient behavioral data exists.
- Source policy, robots restrictions and provenance preservation are mandatory acquisition invariants.
- No proxy rotation, stealth, CAPTCHA bypass or anti-bot bypass is approved.

The full decision, qualification evidence, trade-offs and rejected alternatives are authoritative in `docs/architecture/ADR-001-DISCOVERY-ENGINE.md`.

## Technology stack

Discovery-engine stack is governed by ADR-001. The VS-02 kernel package lives under `services/discovery` and uses direct PostgreSQL migrations rather than an ORM or generic repository layer.

Mobile/application stack remains to be completed in this TRD.

## Modules and data ownership

The discovery kernel owns these stable domain concepts:

- `SourcePolicy` — approved acquisition mode and policy evidence.
- `SourceObservation` — immutable source evidence captured at a specific observed time.
- `CanonicalEntity` — Ziras-owned business/place/product entity identity.
- `Discovery` — normalized deal, event, opening, product/menu or other local signal.
- `Evidence` — field-level provenance linking normalized values to observations.
- `Freshness` — live/likely/unverified/expired state.
- `Interest`, `Interaction`, `Watch` — user-intelligence contracts; persistence/behavioral learning may evolve independently.

Infrastructure volatility is limited to narrow ports:

- `BrowserRenderer`
- `Geocoder`
- `JobQueue`
- `Ranker`

Source-family logic belongs in `SourceAdapter` implementations. Domain code must not import Photon, Huey or Playwright directly.

## Authentication

To be completed in a user/account slice. VS-02 uses no end-user authentication.

## Authorization

To be completed in a user/account slice. Production source authorization is independent of user authorization and remains governed by SourcePolicy.

## Persistence and migrations

Discovery persistence baseline: PostgreSQL 16 + PostGIS + pgvector.

VS-02 migration `services/discovery/migrations/001_discovery_kernel.sql` establishes:

- `source_policy`
- append-only `source_observation`
- `source_state` as the latest accepted observation per source
- `canonical_entity` with PostGIS `geography(Point,4326)`
- `discovery` with freshness, prices, validity window and optional pgvector embedding
- `discovery_evidence` linking normalized fields back to immutable source observations

`promote_source_state()` performs an atomic upsert with a timestamp guard: an incoming observation updates source state only when `incoming.observed_at > current.last_observed_at`. This is the database-level protection against out-of-order workers regressing source state.

Migration rules:

- migrations are forward-only and versioned;
- production migration execution requires a later governed deployment/release slice;
- observations remain append-only evidence;
- canonical/current state may be updated only through monotonic or explicitly versioned rules;
- no destructive retention policy is approved yet.

## External integrations

All external acquisition, geocoding and source-family dependencies must remain behind ADR-001 boundaries and require explicit source/provider policy before production use.

VS-02 includes only a generic structured-HTML normalization adapter and fixture-based tests. It does **not** enable vendor-specific production crawling.

### Meta Ad Library

VS-03 adds a Meta Ad Library source adapter for public Facebook/Instagram advertising evidence using the official Meta API only.

Architecture rules:

- source key: `meta_ad_library`;
- endpoint family: Meta Graph API `/ads_archive`;
- Malta-first reached-country default: `MT`;
- publisher platforms default to `FACEBOOK` + `INSTAGRAM`;
- ad type defaults to `ALL` and active status to `ACTIVE`;
- results enter Ziras as `SourceObservation` evidence, not as automatically trusted `Discovery` objects;
- no Facebook/Instagram HTML scraping is permitted by this integration;
- production collection remains disabled until SourcePolicy and runtime credentials are explicitly approved/configured.

The adapter tracks these enablement dependencies and fails closed when any are missing:

- Meta/Facebook identity-location onboarding complete;
- Meta for Developers account ready;
- Meta Platform Policy accepted;
- Meta app ID configured;
- Ad Library API access confirmed;
- access token available only from secret storage;
- supported Graph API version explicitly pinned;
- `meta_ad_library` SourcePolicy approved;
- reached-country list configured;
- publisher-platform list configured;
- feature enable flag set.

Security rules for the Meta adapter:

- real access tokens must never be committed;
- access tokens are sent using the Authorization header rather than persisted request URLs;
- any `access_token` query parameter returned inside an ad snapshot URL is removed before storing evidence;
- raw Meta `paging.next` URLs are not persisted; only the pagination cursor is retained;
- API errors are explicit failures and must not silently produce empty/verified discovery state.

Operational setup is documented in `docs/integrations/META-AD-LIBRARY.md` and environment names are listed in `services/discovery/config/meta-ad-library.env.example`.

## Deployment

To be completed. Photon production deployment/provider choice remains open and must not rely on the public demo endpoint for production workload.

Meta Ad Library deployment must use deployment secret storage for the access token and must not enable `META_AD_LIBRARY_ENABLED` until the configuration readiness state is `ready` and the source-policy gate is approved.

## Observability

Before production acquisition is enabled, Ziras must expose at minimum:

- source acquisition outcome and policy denial reason;
- static vs browser-fallback rate;
- adapter failures by source family;
- latest accepted observation time and stale-observation rejection count;
- freshness decisions and explicit-expiry rejection count;
- entity-resolution merge/review outcomes;
- queue failures/retries and task age;
- Meta Ad Library readiness state and missing dependency names;
- Meta API success/error/rate-limit outcomes without recording secrets;
- Meta record counts by publisher platform and reached-country query.

## Security

- Source acquisition is fail-closed: unknown/unapproved sources are denied.
- Production source permissions are separate from technical fetch capability.
- Robots and source policy must be respected.
- No stealth, proxy rotation, CAPTCHA bypass or anti-bot bypass is approved.
- Raw evidence/provenance must be retained for any AI-assisted normalization.
- URLs and fetched content must be treated as untrusted input; SSRF/network-boundary controls are required before live acquisition is enabled.
- Meta access tokens and other provider credentials must be held only in deployment secret storage and redacted from URLs, evidence, logs and metrics.

## Performance and reliability

- Static acquisition is preferred; browser rendering is fallback-only.
- Older crawl results must never overwrite newer source state.
- Explicit expiry always overrides relevance/value ranking.
- PostgresHuey throughput and browser-rendering cost must be measured before scale assumptions are accepted.
- pgvector is sufficient for MVP semantic retrieval; a separate vector database requires a new architecture decision.
- Meta pagination uses cursors and must be retry/idempotency safe before scheduled production collection is enabled.

## Testing strategy

The OSS qualification harness on `research/oss-qualification` is retained as architecture evidence.

VS-02 adds deterministic tests for:

- fail-closed source policy;
- user-share-only policy enforcement;
- explicit expiry;
- stale/equal observation rejection;
- entity collision (`Smart Supermarket` vs `Smart Mobility`);
- corroborated same-entity matching;
- deterministic relative-date parsing;
- structured JSON-LD product/offer normalization without AI;
- real PostgreSQL migration execution with PostGIS + pgvector;
- atomic monotonic `source_state` promotion.

VS-03 adds deterministic tests for:

- Meta capability disabled by default;
- complete missing-dependency reporting;
- Malta `MT` + Facebook/Instagram configuration;
- official `/ads_archive` query parameter construction;
- access token absence from request URLs and persisted observations;
- snapshot URL credential stripping;
- cursor-only pagination persistence;
- SourcePolicy approval requirement before creating an allow policy;
- Meta API error propagation without live credentials.

## Operational constraints

- Browser rendering is fallback-only.
- Explicitly expired discoveries must not surface as active.
- Older crawl results must not overwrite newer observations.
- AI normalization must retain original evidence and confidence/provenance.
- Production source permissions are separate from technical fetch capability.
- No vendor-specific production crawling is enabled by VS-02.
- Meta Ad Library collection is disabled by default and is not production-enabled by VS-03.
- Facebook/Instagram scraping is not an approved fallback for Meta API failure.

## Open decisions

- Production hosting/provider for Photon or alternate geocoder implementation.
- Final API/runtime deployment provider.
- Observation/evidence retention periods and deletion/privacy policy.
- Authentication/authorization model for user-facing product services.
- Embedding model and fixed pgvector dimension before ANN indexing is introduced.
- Production Meta app/account ownership and token-rotation process.
- Production Meta collection cadence and query strategy after API access is configured.
