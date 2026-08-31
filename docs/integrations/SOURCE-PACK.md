# Malta Source Pack Operations

Status: implemented as VS-04 candidate source profiles; no candidate source is production-enabled.

## Principle

A useful source and an allowed source are different things.

Ziras therefore tracks two independent questions:

1. **Can the engine technically normalize this source?**
2. **Is automated collection currently permitted and approved?**

Technical support never overrides policy.

## Source matrix

### `visitmalta_events`

- Source: VisitMalta / Malta Tourism Authority
- Kind: events
- Entry: `https://www.visitmalta.com/en/events-in-malta-and-gozo/`
- Terms: `https://www.visitmalta.com/en/terms-and-conditions/`
- Initial policy stage: `review_required`
- Candidate registry: `DENY`
- Candidate access: public web only after policy + robots review
- Robots required: yes
- Browser fallback: permitted technically, but only after policy approval
- Current usefulness evidence: dated public event catalogue and sitemap are available

### `deal_mt`

- Source: Deal.com.mt
- Kind: deals
- Entry: `https://deal.com.mt/`
- Initial policy stage: `partner_required`
- Candidate registry: `DENY`
- Promotion path: after explicit partner/API/feed permission, register a reviewed `PARTNER_ONLY` SourcePolicy; runtime then also requires partner execution context
- Robots required: yes where web access is used
- Current usefulness evidence: active Malta deal catalogue across food, activities, hotels and retail

### `scan_malta`

- Source: SCAN Malta
- Kind: retail
- Entry: `https://www.scanmalta.com/`
- Initial policy stage: `review_required`
- Candidate registry: `DENY`
- Candidate signals: product availability, special price, price drop, new product

### `greens_malta`

- Source: Greens Supermarket
- Kind: retail/supermarket
- Entry: `https://www.greens.com.mt/`
- Initial policy stage: `review_required`
- Candidate registry: `DENY`
- Candidate signals: grocery product availability, promotion, price change

### `decathlon_malta`

- Source: Decathlon Malta
- Kind: retail
- Entry: `https://www.decathlon.mt/`
- Initial policy stage: `review_required`
- Candidate registry: `DENY`
- Candidate signals: sale, price drop, new product

### `atrium_malta`

- Source: The Atrium Malta
- Kind: retail
- Entry: `https://www.atrium.com.mt/`
- Initial policy stage: `review_required`
- Candidate registry: `DENY`
- Candidate signals: sale, promotion, new product

### `pizza_hut_malta`

- Source: Pizza Hut Malta
- Kind: restaurant
- Entry: `https://www.pizzahut.com.mt/`
- Initial policy stage: `review_required`
- Candidate registry: `DENY`
- Candidate signals: menu offer, limited promotion, new menu item

### `shows_happening`

- Source: ShowsHappening
- Kind: events/ticketing
- Entry: `https://www.showshappening.com/`
- Initial policy stage: `partner_required`
- Candidate registry: `DENY`
- Promotion path: approved official feed/API/partnership → reviewed `PARTNER_ONLY` policy → partner execution context

## Promotion path for a source

A review-required source moves toward production only through:

`candidate profile (DENY)` → `terms/robots/licensing review` → `approved SourcePolicy` → `fixture tests` → `live smoke test` → `freshness/error telemetry` → `production-enable approval`

For partner sources:

`candidate profile (DENY)` → `partner/API/feed agreement` → `PARTNER_ONLY policy approval` → `credentials/feed config` → `partner-context smoke test` → `production-enable approval`

A caller-provided `partner=True` flag is never sufficient without the approved policy record.

## Runtime invariants

- Unknown source key: deny.
- Review-required source without approved policy: deny.
- Partner-required source without approved `PARTNER_ONLY` policy: deny.
- Approved partner-only source without partner execution context: deny.
- Non-HTTPS source URL: reject.
- Host outside the source profile's domain allowlist: reject.
- Browser fallback is never permission to bypass source restrictions.
- Robots requirements are retained in the source policy record.
- Raw HTML acquisition and parsing remain separate responsibilities.
- Structured extraction is deterministic before AI.
- Downstream entity resolution/freshness still decides whether a source observation becomes a useful live discovery.

## When to introduce a bespoke adapter

Do not add source-specific parsing merely because a website has different markup.

A bespoke adapter is justified only when at least one of these is true:

- the source provides an official API/feed with its own schema;
- critical data is not represented in supported structured metadata;
- the source has a stable machine-readable payload that materially improves correctness;
- deterministic source-specific semantics are needed for validity/expiry/location;
- the generic profile cannot meet measured extraction-quality targets.

Any bespoke adapter must retain the same SourcePolicy, provenance, domain, freshness and test boundaries.

## Metrics for VS-04 and later source enablement

Per source:

- policy readiness;
- observations/day;
- discovery candidates/day;
- normalization success rate;
- duplicate rate;
- explicit expiry coverage;
- entity-resolution ambiguity rate;
- stale/invalid-on-open rate;
- static acquisition success rate;
- browser-fallback rate;
- HTTP/error/rate-limit rate;
- last successful observation time.

Portfolio-level POC targets remain:

- at least 50 useful discoveries/day;
- at least 90% valid when opened;
- less than 5% stale/expired surfaced;
- less than 5% duplicate rate;
- at least 5 independent source types;
- at least 70% relevance to selected interests;
- zero merchant onboarding.
