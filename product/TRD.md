# Technical Requirements Document

Status: Draft v0.1 — requires explicit technical approval before runtime implementation

## Architecture

Ziras uses the PES Mobile template and follows a **modular monolith / vertical-slice** architecture.

Initial system boundaries:

1. **Mobile application** — Expo / React Native consumer experience.
2. **Discovery application layer** — source registry, ingestion orchestration, extraction, entity resolution, freshness, ranking and watches.
3. **Persistence** — canonical Ziras entities/discoveries/users/interests/source metadata.
4. **External adapters** — permitted web sources, APIs/feeds, search providers and user-shared content.

Do not introduce microservices for the POC. Source collectors are adapters behind contracts and may run as scheduled/background jobs within the same deployable backend until scale or isolation requirements justify separation through an ADR.

## Technology stack

### Mobile — existing template
- Expo `~57`
- React Native `0.86`
- React `19.2`
- Expo Router
- TypeScript
- React Native Reanimated for approved motion
- Expo Secure Store for future sensitive local tokens

Exact mobile versions remain governed by `apps/mobile/package.json` and Expo-compatible install tooling.

### Backend — proposed
- TypeScript / Node.js runtime.
- HTTP JSON API using the simplest framework already approved/introduced during implementation planning.
- PostgreSQL for canonical relational persistence and geospatially-indexable coordinates.
- Background job execution for discovery refresh/verification; keep implementation provider-neutral.

Redis/queues are **not required initially** unless measured throughput/retry needs justify them.

### AI/model boundary
LLMs may assist structured extraction/classification and semantic tagging, but core freshness/expiry, source-policy enforcement, deduplication keys and safety gates must remain deterministic where possible.

Model providers must be adapter-based and must not become the canonical source of truth.

## Modules and data ownership

### `source-policy`
Owns source registry and whether/how a source may be accessed.

Core fields:
- sourceId
- domain/provider
- accessMode (`PUBLIC_WEB`, `API`, `PARTNER`, `USER_SHARED`, `DEEPLINK_ONLY`, `DISABLED`)
- policyStatus
- crawlFrequency
- reliabilityScore
- lastSuccessAt
- allowedContentTypes

No collector executes when policyStatus does not allow the configured access mode.

### `discovery-ingestion`
Owns raw source observations and normalisation requests.

Responsibilities:
- collect permitted source observations;
- retain provenance;
- enqueue/process extraction;
- avoid presenting raw observations directly to consumers.

### `discovery`
Owns canonical `Discovery` records.

Minimum fields:
- id
- type
- entityId/locationId
- title/summary
- originalPrice/currentPrice/discount when applicable
- startsAt/expiresAt
- source references
- discoveredAt
- lastVerifiedAt
- freshnessState
- confidence
- interest tags

### `entity`
Owns canonical businesses, places, brands and locations.

Third-party IDs (for example a place/provider ID) are cross-references only.

### `freshness`
Owns freshness state transitions:
- `VERIFIED`
- `LIKELY_ACTIVE`
- `UNVERIFIED`
- `EXPIRED`

Rules use explicit expiry, source disappearance/change, verification age, source reliability and corroboration. Expired records are excluded from active recommendation queries.

### `interest`
Owns hierarchical interest taxonomy and user interest weights.

Initial user interests come from onboarding. More specific weights are learned from behaviour without requiring deeper onboarding questions.

### `ranking`
Produces a deterministic base score from:
- distance/location relevance
- freshness
- interest relevance
- value/deal strength
- novelty
- urgency

Behavioural learning may adjust weights, but the score inputs must remain inspectable for debugging.

### `watch`
Owns user monitors such as a brand/place/category/threshold and their notification eligibility.

### `share`
Owns shareable discovery representations and future user-shared ingestion.

## Authentication

POC decision remains open.

Preferred sequence:
- allow anonymous/local first-run discovery where practical;
- introduce account authentication only when cross-device sync, persistent watches or abuse controls require it.

Do not block the first-value experience behind mandatory account creation without a product decision.

## Authorization

- Consumers may modify only their own preferences, watches and saved items.
- Internal ingestion/admin operations require server-side privileged authorization when introduced.
- Source-policy changes are never writable from the consumer app.

## Persistence and migrations

Proposed PostgreSQL tables/bounded aggregates:
- `sources`
- `source_observations`
- `entities`
- `entity_external_refs`
- `locations`
- `discoveries`
- `discovery_sources`
- `interest_taxonomy`
- `user_interest_weights`
- `user_actions`
- `watches`
- `saved_discoveries`

Use migrations; never mutate production schema manually.

Raw source payload retention must be minimised and governed by source/licensing/privacy requirements rather than retained indefinitely by default.

## External integrations

Integration categories:
- permitted official websites;
- official APIs/feeds;
- event feeds;
- affiliate/partner APIs;
- geocoding/entity-resolution providers;
- user-shared URLs/content where allowed.

### Hard boundary
Do not implement automated collection against sources whose terms prohibit it. Such providers must be `DEEPLINK_ONLY`, partner/API based or disabled until permitted access exists.

## Deployment

Provider selection is deferred. Architecture remains provider-neutral.

POC deployment requires:
- backend API/job runtime;
- PostgreSQL;
- scheduled job capability;
- secrets management;
- HTTPS;
- basic logs/metrics.

No production provider decision is implied by this TRD.

## Observability

Minimum POC metrics:
- observations collected/source/day;
- successful/failed source checks;
- extraction failures;
- entity resolution ambiguity rate;
- duplicates removed;
- discoveries created/day;
- verification success rate;
- stale/expired surfaced rate;
- source latency/error rate;
- feed relevance feedback.

Every surfaced discovery must retain provenance sufficient to explain why it exists and when it was last verified.

## Security

- No credentials in mobile bundles or Git.
- Server-side secrets only.
- Validate/normalise untrusted external content before storage/rendering.
- Prevent server-side request forgery in URL ingestion/collector infrastructure.
- Apply rate limits and host allow/policy controls to collectors.
- Do not follow arbitrary redirects into private/internal address ranges.
- Sanitise generated/extracted text before rendering/share pages.
- Treat precise location history as sensitive; retain only what is necessary for product function.
- Permission-denied flows must remain usable via manual location.

A dedicated security review is required before user-supplied URL ingestion or production web collection is enabled.

## Performance and reliability

POC goals:
- feed API should return cached/precomputed ranked results quickly enough for consumer mobile UX;
- collector failures are isolated per source;
- one failed source must not stop other discovery ingestion;
- retries are bounded with backoff;
- stale source data must degrade to labelled/unavailable rather than being silently presented as verified.

## Testing strategy

### Deterministic tests
- source-policy gate tests;
- expiry/freshness state-machine tests;
- deduplication tests;
- entity-resolution rules;
- ranking rules;
- onboarding state/navigation;
- permission-denial/manual-location flow.

### Integration tests
- source adapter fixture tests using stored fixtures rather than uncontrolled live sites in CI;
- persistence/migration tests;
- API contract tests.

### POC validation
Live source tests run outside deterministic CI and record source, time, outcome and freshness evidence.

### Mobile
- typecheck/lint;
- accessibility checks;
- real-device splash/onboarding verification;
- reduced-motion behaviour;
- deep-link tests when introduced.

## Operational constraints

- Source freshness is the primary operational quality target.
- No merchant onboarding dependency.
- No production crawling without approved source-policy entries.
- No autonomous production enablement/deployment.
- EAS build/submit/OTA actions remain human-approved PES gates.

## Open decisions

1. Backend framework and workspace placement (`apps/api` or equivalent) after technical approval.
2. PostgreSQL provider/deployment provider.
3. Geocoding/entity-resolution provider and caching/licensing strategy.
4. Model provider(s) for structured extraction/classification.
5. Anonymous-first versus account-enabled POC persistence.
6. Notification provider/strategy when Watch alerts enter scope.
7. Exact production source inventory after per-source policy review.
