# ADR-001 — Ziras Discovery Engine Architecture

Status: **PROPOSED — awaiting explicit architecture approval**

Date: 2026-08-31

Research branch: `research/oss-qualification`
Qualification head used for final queue gate: `8c522118eaeaf606a07aa0483228e5de67f536b2`

## Context

Ziras needs a durable discovery engine that can continuously discover local offers, launches, events, products, restaurant promotions and other timely signals across heterogeneous public sources without depending on one fragile crawler or paid extraction vendor.

The qualification spike tested multiple acquisition frameworks and the supporting discovery operations across a broad Malta-oriented vendor/source matrix. The goal was to minimize infrastructure and framework overlap while preserving replaceable external boundaries.

The current PRD and TRD are still Draft skeletons, so this ADR does not override an already-approved product or technical requirement. It must remain Proposed until explicitly approved.

## Decision candidate

Adopt a **Python modular-monolith discovery kernel** with static-first acquisition, browser rendering only as fallback, deterministic extraction before AI, and PostgreSQL as the primary operational/data backbone.

### 1. Acquisition

**Core:**
- Python 3.12
- Scrapy `2.18.0`
- `scrapy-playwright==0.0.48` as browser fallback only

Rules:
- Respect `robots.txt` and per-source policy.
- No proxy rotation, stealth mode, CAPTCHA bypass or anti-bot bypass in the core.
- Use API/feed/source-specific adapters before generic page crawling when available.
- Prefer static HTTP acquisition; invoke Chromium only when the static response lacks the required discovery signal.
- Keep concurrency and per-domain rate limits explicit and conservative.

Evidence:
- Scrapy passed the static acquisition qualification.
- Scrapy + Playwright passed the qualified dynamic samples including Atrium, VisitMalta, Deal.com.mt, Decathlon, Greens, Pizza Hut, Scan and ShowsHappening.
- Crawl4AI and Crawlee also worked, but no longer justify their overlapping production dependency surface once Scrapy + Playwright covers both static and rendered acquisition.

### 2. Extraction and normalization

Pinned qualification dependencies:
- `httpx==0.28.1`
- `beautifulsoup4==4.13.4`
- `lxml==6.1.2`
- `extruct==0.18.0`
- `trafilatura==2.2.0`
- `dateparser==1.4.2`
- `price-parser==0.5.1`
- `RapidFuzz==3.14.5`

Order of extraction:
1. Structured metadata / JSON-LD with Extruct.
2. Source-specific deterministic selectors.
3. Main-content extraction with Trafilatura where useful.
4. Price/date normalization.
5. AI extraction only for unresolved ambiguous content, behind a separate policy boundary.

Date handling is a cascade, not Dateparser alone:
1. explicit/structured timestamps;
2. deterministic relative-date rules;
3. Dateparser;
4. AI fallback only if still unresolved.

### 3. Entity resolution

RapidFuzz is **candidate generation only**, never entity identity.

Resolution priority:
1. stable external/source identifier when available;
2. normalized name similarity;
3. category compatibility;
4. geographic proximity/address evidence;
5. source/domain evidence.

A name-only match must never merge entities. Qualification explicitly rejected the `Smart Supermarket` vs `Smart Mobility` collision despite high name similarity.

### 4. Persistence, nearby search and semantic interests

Use one PostgreSQL 16 backbone with:
- PostGIS for geospatial data and radius queries;
- pgvector for semantic interest/item embeddings and similarity retrieval.

Qualification:
- PostGIS radius query passed for the Malta test set.
- pgvector semantic retrieval passed.

Do **not** introduce a separate vector database or geo database for MVP.

### 5. Background jobs and scheduling

Use Huey `3.3.4` with PostgreSQL storage through a narrow `JobQueue` boundary.

Qualified operations:
- enqueue/dequeue;
- task execution and result storage;
- retries, retry delay and backoff metadata;
- priorities;
- delayed scheduling.

MVP consequence: **Redis is not required** for the discovery engine.

If measured production load later shows PostgreSQL queue contention or throughput limitations, the `JobQueue` boundary permits migration without changing discovery domain logic.

### 6. Geocoding

Use Photon behind a narrow `Geocoder` boundary.

Qualification passed Malta forward-geocoding samples for Sliema, Birkirkara, Valletta, St Julian's, Mellieħa and Mdina plus reverse geocoding.

Production rule:
- Do not depend on the public Photon demo service for production workload.
- Self-host Photon or select another approved geocoder implementation behind the same boundary.

### 7. Ranking

MVP ranking stays deterministic and explainable:

`score = interest relevance + distance + freshness + value/quality + contextual fit`

Use pgvector as an input to interest relevance, not as the whole ranking model.

`implicit==0.7.3` has been pre-qualified for collaborative recommendation, but it is **not an MVP kernel dependency**. Activate only after Ziras has enough behavioral interaction data to justify collaborative filtering.

### 8. Selector resilience

Scrapling `0.4.8` passed the adaptive-selector qualification and may be used as an **optional bounded resilience component** for sources with frequent DOM drift.

It is not the core fetcher, and stealth/anti-bot functionality is outside this decision.

## Explicitly not selected for the MVP core

- Crawl4AI — capable but overlaps with Scrapy + Playwright.
- Crawlee — capable but overlaps with the selected acquisition path.
- Firecrawl — not required for the qualified discovery path.
- changedetection.io — not required; freshness/change detection belongs inside the source-observation pipeline.
- Redis — not required after PostgresHuey qualification.
- Elasticsearch/OpenSearch — not required for MVP discovery retrieval.
- Pinecone/Qdrant/Weaviate or another standalone vector database — pgvector is sufficient for the qualified use case.
- Splink — not justified initially; entity resolution requirements are currently narrower.
- `implicit` as a mandatory dependency — defer until behavioral data exists.

## Architectural boundaries

Keep only boundaries that protect real volatility; do not introduce generic repositories or event buses mechanically.

Required boundaries:
- `SourcePolicy` — whether/how a source may be acquired.
- `SourceAdapter` — source-family acquisition + deterministic extraction behavior.
- `BrowserRenderer` — rendered-page fallback.
- `Geocoder` — Photon or alternate provider.
- `JobQueue` — PostgresHuey or future queue implementation.
- `Ranker` — deterministic MVP ranker with optional future learned implementations.

PostgreSQL persistence can be implemented directly inside the modular monolith's owning modules; no generic repository abstraction is required.

## Operational invariants

- Preserve source URL, observed timestamp and extraction provenance for every discovery observation.
- Separate an observation from the canonical entity it may resolve to.
- Never overwrite a newer observation with an older crawl result.
- Keep crawl/render failures observable by source and adapter.
- Browser fallback must be measurable so rendering cost can be controlled.
- Source policy denial is a valid terminal outcome, not a crawler failure.
- AI-generated normalization must retain the original extracted evidence and confidence/provenance.

## Evidence summary

Qualification covered heterogeneous source classes including supermarkets, fashion, electronics, home retail, restaurants, deal/loyalty sites, cinemas, events/ticketing, tourism and local discovery sources, with policy-gated controls for sources that should not be silently crawled.

The completed qualification demonstrated:
- static acquisition;
- rendered fallback;
- structured/main-content extraction;
- price normalization;
- explicit and relative-date normalization;
- collision-resistant entity resolution;
- Malta forward and reverse geocoding;
- PostGIS proximity queries;
- pgvector similarity retrieval;
- PostgreSQL-backed job execution and scheduling;
- optional adaptive selector recovery;
- optional collaborative recommendation.

## Consequences

Benefits:
- one primary datastore;
- no Redis requirement for MVP;
- no separate vector/search infrastructure;
- one crawl framework with one browser fallback integration;
- deterministic behavior before AI;
- narrow replacement points for genuinely external/volatile capabilities;
- lower deployment and maintenance surface.

Trade-offs:
- browser-rendered sources remain more expensive than static sources;
- PostgresHuey throughput must be measured before high-scale expansion;
- Photon self-hosting has operational cost if selected for production;
- source-specific adapters remain necessary for high-quality extraction;
- collaborative recommendation is intentionally deferred until enough data exists.

## Approval required

This ADR becomes `APPROVED` only after an explicit architecture approval. Approval should then be reflected in the TRD and governed delivery records before production runtime implementation begins.
