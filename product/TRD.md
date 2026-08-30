# Technical Requirements Document

Status: Draft

## Architecture

The Ziras discovery-engine architecture baseline is **approved** by `ADR-001 — Ziras Discovery Engine Architecture` and `DEC-01`.

Approved discovery-engine direction:

- Python modular-monolith discovery kernel.
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

Discovery-engine stack is governed by ADR-001. Mobile/application stack remains to be completed in this TRD.

## Modules and data ownership

To be completed. Discovery domain must retain stable ownership of `SourcePolicy`, source observations, canonical entities, discoveries, evidence/provenance, freshness, interests, interactions and watches.

## Authentication

To be completed.

## Authorization

To be completed.

## Persistence and migrations

Discovery persistence baseline: PostgreSQL 16 + PostGIS + pgvector. Detailed schema and migration policy remain to be specified before runtime implementation.

## External integrations

All external acquisition, geocoding and source-family dependencies must be behind the approved narrow boundaries in ADR-001 and must have explicit source/provider policy before production use.

## Deployment

To be completed. Photon production deployment/provider choice remains open and must not rely on the public demo endpoint for production workload.

## Observability

To be completed. At minimum, source acquisition status, browser-fallback rate, adapter failures, freshness decisions and queue failures must be observable.

## Security

To be completed. Discovery acquisition must remain policy-gated, robots-aware and must not use prohibited bypass techniques.

## Performance and reliability

To be completed. PostgresHuey throughput and browser-rendering cost must be measured before scale assumptions are accepted.

## Testing strategy

The OSS qualification harness on `research/oss-qualification` is retained as architecture evidence. Production tests must additionally cover source adapters, freshness, entity collision cases, idempotency and policy denials.

## Operational constraints

- Browser rendering is fallback-only.
- Explicitly expired discoveries must not surface as active.
- Older crawl results must not overwrite newer observations.
- AI normalization must retain original evidence and confidence/provenance.
- Production source permissions are separate from technical fetch capability.

## Open decisions

- Production hosting/provider for Photon or alternate geocoder implementation.
- Final API/runtime deployment provider.
- Detailed discovery persistence schema and retention policy.
- Authentication/authorization model for user-facing product services.
