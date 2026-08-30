# Ziras OSS Qualification Spike

## Purpose

Select the smallest durable open-source stack for Ziras discovery before product runtime implementation. Popularity alone is not evidence: candidates must survive reproducible source-class tests.

## Safety / policy boundary

- Research only; no production collection is authorised.
- Public pages only.
- Respect `robots.txt` where the client supports it; preflight it for browser tests.
- No credentials, authenticated sessions, residential/datacenter proxies, CAPTCHA solving, stealth mode, fingerprint spoofing, or anti-bot bypass.
- At most one low-rate page request per configured source per adapter run.
- A technical PASS never grants production source-policy permission.
- Policy-gated controls such as Wolt, Zara and Cloudigo are recorded but skipped by automated live tests.

## Source classes

The matrix in `sources.json` deliberately spans:

- supermarket offer/catalogue pages;
- fashion sale pages;
- electronics and home retail;
- sports retail;
- local deal/discount directories;
- official events;
- ticket marketplaces;
- local-news opening discovery;
- supermarket aggregation;
- policy-gated delivery/fashion/deal platforms.

## Candidate operations

| Operation | Candidates | Qualification intent |
| --- | --- | --- |
| Static acquisition/orchestration | Crawlee Parsel, Scrapy, plain HTTP baseline | Reliability, robots, retries, low operational surface |
| Browser fallback | Crawlee Playwright, Crawl4AI | JS-rendered content without stealth/anti-bot bypass |
| Selector resilience | Scrapling parser adaptive mode | Survive benign DOM refactors without using its stealth fetchers |
| Semantic markup extraction | extruct | JSON-LD/Microdata/OpenGraph before AI extraction |
| Change detection | URL/content fingerprints; urlwatch candidate | Avoid hard dependency until live-change tests justify one |
| Entity resolution | deterministic rules + RapidFuzz; Splink candidate | Canonical business/location deduplication |
| Geo | libpostal + Photon + PostGIS | Malta address normalisation, geocoding and radius search |
| Semantic interests | pgvector | Keep embeddings with canonical PostgreSQL data |
| Behaviour ranking | deterministic first; implicit later | Add collaborative signals only after behaviour data exists |

## PASS does not mean “scrape this source”

The test asks whether a component can technically acquire/parse a source class under conservative settings. Production access remains governed per source by Ziras `SourcePolicy` and legal/terms review.

## Primary acceptance measures

- useful body/offer signal present;
- source failures isolated;
- robots/policy controls respected;
- browser fallback materially improves JS-heavy cases;
- no stealth feature needed;
- adaptive parsing survives a controlled DOM change;
- results are machine-readable GitHub Actions artifacts.

The final architecture should prefer one durable acquisition/orchestration framework plus narrowly-scoped libraries for capabilities that are genuinely differentiated.
