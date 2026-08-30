# Product Requirements Document

Status: Approved — product scope baseline v0.1
Approved by: Product owner (`ksazid`)
Approved at: 2026-08-31T00:46:15+02:00

## Product objective

Ziras is a Malta-first consumer discovery app that answers **“what’s nearby?”** by finding fresh, relevant local discoveries without requiring merchants to onboard.

The product continuously discovers permitted/public signals such as deals, promotions, openings, events, launches and noteworthy nearby experiences, verifies freshness, resolves them to real places, and ranks them for each user using location, interests and behaviour.

## Target users

- Malta residents who want relevant nearby discoveries without checking many apps/sites.
- Visitors who want timely local recommendations around their current location.

## User roles

### Consumer
Receives personalised discoveries, saves/shares them, creates watches and gives implicit/explicit relevance feedback.

### System
Collects permitted source data, normalises discoveries, verifies freshness, resolves entities and ranks results.

Merchants are **not** an MVP user role and do not need to onboard.

## Core journeys

1. **Launch** — animated Ziras logo → “what’s nearby.” transition → onboarding/home.
2. **Onboard** — user grants/chooses location → selects a small set of broad interests → sees the feed immediately.
3. **Discover** — user sees a ranked “For You” feed of nearby discoveries.
4. **Explore nearby** — user browses nearby discoveries by list/map and category.
5. **Act** — user opens the original source/provider, saves or shares a discovery.
6. **Watch** — user follows a brand/place/category/condition such as “Indian food offers nearby”.
7. **Learn** — Ziras updates interest weights from opens, saves, shares, hides and repeated behaviour.
8. **Contribute** — user may share a URL/screenshot into Ziras for extraction and verification; this is optional and later in the MVP sequence.

## Functional requirements

### Brand and launch
- `REQ-BRD-001` — The product name is **Ziras**.
- `REQ-BRD-002` — The public tagline is **“what’s nearby.”**
- `REQ-BRD-003` — App launch shows an animated Ziras logo before the tagline transition.
- `REQ-BRD-004` — The tagline transition completes before loading onboarding/home.

### Onboarding
- `REQ-ONB-001` — First-run onboarding must be no more than two required screens.
- `REQ-ONB-002` — Screen 1 requests current location permission or allows manual location selection.
- `REQ-ONB-003` — Screen 2 allows quick multi-select of broad interests.
- `REQ-ONB-004` — Detailed sub-interests must not be required during onboarding.
- `REQ-ONB-005` — Ziras must infer more specific interests over time from behaviour.
- `REQ-ONB-006` — The user must be able to reach the first personalised feed immediately after onboarding.

### Discovery
- `REQ-DIS-001` — Ziras normalises source signals into a universal Discovery model.
- `REQ-DIS-002` — MVP discovery types are `DEAL`, `OPENING`, `EVENT`, `PRICE_DROP`, `NEW_PRODUCT`, `NEW_MENU`, `HAPPY_HOUR`, and `TRENDING`.
- `REQ-DIS-003` — Each discovery must reference an original source URL or permitted deep link when available.
- `REQ-DIS-004` — Each discovery must resolve to a location/business entity where applicable.
- `REQ-DIS-005` — The system must deduplicate equivalent discoveries from multiple sources.
- `REQ-DIS-006` — Merchants are not required to create or maintain listings for MVP coverage.

### Freshness and trust
- `REQ-FRS-001` — Every discovery has a freshness state: `VERIFIED`, `LIKELY_ACTIVE`, `UNVERIFIED`, or `EXPIRED`.
- `REQ-FRS-002` — Expired discoveries must not appear as active recommendations.
- `REQ-FRS-003` — The system records `discoveredAt` and `lastVerifiedAt`.
- `REQ-FRS-004` — The POC target is under 5% stale/expired recommendations reaching users.
- `REQ-FRS-005` — The POC target is at least 90% of surfaced discoveries valid when opened.

### Personalisation
- `REQ-PER-001` — Ranking uses location, distance, freshness, interest relevance, value, novelty and urgency.
- `REQ-PER-002` — Ziras maintains weighted user interests rather than a flat category list.
- `REQ-PER-003` — User actions such as open, save, share and “not interested” influence future ranking.
- `REQ-PER-004` — The feed should favour fewer high-relevance items over exhaustive deal inventory.

### MVP surfaces
- `REQ-UI-001` — `For You` shows personalised discoveries.
- `REQ-UI-002` — `Nearby` shows geographically relevant discoveries with list/map support.
- `REQ-UI-003` — `Watch` lets users follow brands, places, categories or simple conditions.
- `REQ-UI-004` — `Saved` stores discoveries for later.
- `REQ-UI-005` — Discovery cards support Save, Share, Not interested and Open source actions.

### Viral loop
- `REQ-VIR-001` — Discoveries can be shared outside Ziras using a public/shareable representation.
- `REQ-VIR-002` — A recipient should be able to understand the discovery before installing the app.
- `REQ-VIR-003` — Shared discovery experiences include a clear path to “Find what’s nearby”.

### Source policy
- `REQ-SRC-001` — Every automated source must have an explicit access mode and policy status.
- `REQ-SRC-002` — Ziras must not intentionally bypass authentication, technical controls, robots restrictions, contractual prohibitions or platform scraping restrictions.
- `REQ-SRC-003` — Sources that prohibit scraping may only be used via permitted APIs, partnerships, deep links or user-provided content where lawful.
- `REQ-SRC-004` — Source reliability and last-success metadata must be tracked.

## Business rules

- No merchant onboarding is required for the Malta POC.
- Source legality/permission and data freshness take precedence over catalogue size.
- Ziras owns its canonical entity/discovery identifiers; third-party place IDs are references, not the primary datastore.
- The application must not claim an offer is live when evidence is stale or ambiguous.
- Personalisation starts broad and becomes specific through behaviour; onboarding remains intentionally minimal.

## Out of scope

- Merchant portal.
- Merchant self-service offer creation.
- Checkout or payment processing.
- Coupon issuance/redemption or QR/PIN redemption.
- Full reviews/social network.
- GPS hardware or physical retail integrations.
- Unauthorised scraping of prohibited sources.
- Europe-wide rollout before the Malta POC passes its gates.

## Success metrics

### 14-day discovery-engine POC gates
- At least **50 useful discoveries/day** across the pilot geography.
- At least **90% valid when opened**.
- Less than **5% stale/expired recommendations**.
- Less than **5% duplicates after processing**.
- At least **5 independent source types**.
- At least **70% judged relevant to selected interests**.
- **0 merchant onboarding** required.

### User-value validation
With 10 Malta pilot users, at least 7 should repeatedly answer yes to:

> “Did Ziras tell you something useful you probably would not have discovered yourself?”

## Release scope

### Malta POC geography
- Birkirkara
- Sliema
- Gżira
- St Julian’s
- Valletta

### MVP categories
- Food & drink
- Fashion/retail
- Events/activities
- New openings

## Constraints

- Mobile-first Expo/React Native product using the existing PES Mobile template.
- No production scraping integration without source-policy review.
- Location permissions must be optional/fail gracefully; manual location selection is required as fallback.
- Privacy, permissions, deep links, notifications and offline/stale states follow PES mobile Definition of Done when introduced.

## Open decisions

- Final production data providers/partnerships after source-policy validation.
- Backend hosting/provider selection.
- Authentication strategy for the POC versus post-POC account sync.
- Monetisation is intentionally deferred until the consumer-value hypothesis is validated.
