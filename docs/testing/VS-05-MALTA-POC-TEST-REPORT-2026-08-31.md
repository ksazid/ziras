# VS-05 Malta POC Test Report — 2026-08-31

## Status

**Result: CONDITIONAL PASS — technical ingestion pipeline is validated; product POC success gates are not yet passed.**

This report records the first Malta POC validation after certified VS-05 was merged to `main`.

- `main`: `ea40e78ca4a78b37480186158d5a01ff3fee2184`
- certified VS-05 implementation: `934f3c871232b44be29b026624b34f5868c3b34d`
- post-certification governance head: `99544cf1549a141b65227207cac7d1ee82f204bc`
- post-certification CI: `https://github.com/ksazid/ziras/actions/runs/33376847730`
- scope: POC only
- production source access: NOT APPROVED
- scheduler: OFF
- release: NOT AUTHORIZED
- production-enable: PENDING

## Execution note

The connected GitHub integration available during this validation can inspect and rerun existing Actions jobs but does not expose creation of a new `workflow_dispatch` run. Therefore the repository's `Malta POC Ingestion` workflow was **not falsely marked as executed**.

The validation below combines:

1. exact-head VS-05 CI evidence for ingestion/kernel/PostgreSQL behavior; and
2. a live manual check of the three currently POC-approved Malta sources.

This report does **not** claim formal discoveries/day, duplicate-rate, stale-rate or browser-fallback metrics until the actual POC workflow is executed.

## Technical pipeline validation

| Test area | Result | Evidence |
| --- | --- | --- |
| Acquisition dependencies | PASS | Scrapy + Playwright extras install in CI |
| Source policy/scope/path gate | PASS | VS-05 deterministic tests |
| Request-cap enforcement | PASS | VS-05 deterministic tests |
| Freshness classification | PASS | VS-05 deterministic tests |
| Expired discovery filtering | PASS | VS-05 deterministic tests |
| Stable discovery fingerprint | PASS | VS-05 deterministic tests |
| Cross-source idempotency | PASS | PostgreSQL integration test |
| Observation/provenance persistence | PASS | PostgreSQL integration test |
| PostgreSQL 16 | PASS | CI integration environment |
| PostGIS | PASS | CI integration environment |
| pgvector | PASS | CI integration environment |
| PES preflight | PASS | full repository preflight |

## Live POC source validation

### 1. VisitMalta Events

- source key: `visitmalta_events`
- policy scope: `poc`
- acquisition mode: `browser`
- URL: `https://www.visitmalta.com/en/events-in-malta-and-gozo/`
- live result: page is reachable and exposes the `Browse Events` application shell.
- important finding: event cards are not present in the static response used for this manual check.
- conclusion: **browser fallback is required exactly as VS-04 qualification predicted.**
- formal candidate count: **NOT MEASURED** until Playwright POC workflow execution.

### 2. Eden Cinemas

- source key: `eden_cinemas`
- policy scope: `poc`
- acquisition mode: `static`
- URLs:
  - `https://www.edencinemas.com.mt/special-offers`
  - `https://www.edencinemas.com.mt/whats-on`
- live public inventory observed:
  - 6 named offer entries on Special Offers.
  - 32 listed items on What's On.
  - total visible inventory in reviewed pages: **38 items**.

#### Defect / extraction mismatch

The current catalog assigns `adapter_kind=promotion` to the Eden source entry, including `/whats-on`. The generic promotion extractor is primarily price/percentage-signal driven, while many Eden offers are descriptive and `/whats-on` is semantically event inventory.

**Impact:** the live site contains useful discovery inventory, but the generic current adapter may under-extract it.

**Recommended correction:** split Eden source routes or introduce an Eden-specific adapter so `/special-offers` uses promotion semantics and `/whats-on` uses event semantics.

### 3. Homemate Special Offers

- source key: `homemate_offers`
- policy scope: `poc`
- acquisition mode: `static`
- URL: `https://www.homemate.com.mt/special-offers`
- live result: **`30 of 500 items loaded`** is shown by the site.
- the visible products include original and reduced EUR prices, making this source a strong deterministic deal source.
- examples observed include price pairs such as `€11.50 → €5.90`, `€27.00 → €15.00`, and `€19.90 → €10.90`.

**Finding:** Homemate currently provides enough raw offer inventory to contribute substantial POC volume, but a single page fetch may expose only the first loaded batch unless pagination/lazy-loading is handled explicitly.

## Current source coverage

POC-approved source classes currently represented:

1. events-official — VisitMalta
2. entertainment-offers — Eden Cinemas
3. home-retail — Homemate

Current count: **3 independent POC-approved source classes**.

PRD target: **at least 5 independent source types**.

**Gate result: FAIL — two additional permitted POC source classes are required.**

## PRD POC gate assessment

| POC gate | Target | Current result |
| --- | ---: | --- |
| Useful discoveries/day | >= 50 | NOT MEASURED — formal POC workflow required |
| Valid when opened | >= 90% | NOT MEASURED |
| Stale/expired surfaced | < 5% | NOT MEASURED |
| Duplicate rate after processing | < 5% | NOT MEASURED |
| Independent source types | >= 5 | **FAIL — currently 3** |
| Relevant to selected interests | >= 70% | NOT MEASURED — user-interest evaluation not started |
| Merchant onboarding required | 0 | **PASS** |

## Key findings

1. **VS-05 technical pipeline is green.** The ingestion, policy, dedupe, provenance and database contracts are validated in CI.
2. **Homemate is the strongest current volume source.** It exposes 500 special-offer items and deterministic old/new pricing.
3. **Eden needs source-specific extraction.** Existing generic promotion semantics do not cleanly model the `/whats-on` route.
4. **VisitMalta validates the browser-fallback requirement.** Static acquisition alone is insufficient.
5. **Coverage is below the PRD gate.** Only 3 POC-approved source classes exist; the target is 5.
6. **Formal POC metrics remain unmeasured.** No discoveries/day, duplicate, stale or browser-fallback percentages should be reported until the manual `Malta POC Ingestion` workflow is actually dispatched.

## Defects / follow-up items

### POC-01 — Eden route semantics

**Severity:** Medium  
**Status:** Open

Split Eden `/special-offers` and `/whats-on` extraction semantics or add a dedicated adapter.

### POC-02 — VisitMalta browser execution evidence

**Severity:** Medium  
**Status:** Open

Execute Playwright-backed ingestion and record candidate count, browser success and extraction quality.

### POC-03 — POC source coverage

**Severity:** High for product validation  
**Status:** Open

Qualify and approve at least two additional independent Malta source classes before claiming the five-source POC gate.

### POC-04 — Formal metric run

**Severity:** High for validation evidence  
**Status:** Open

Run the repository `Malta POC Ingestion` workflow in `poc` scope and capture its artifact for discoveries/day, unique count, duplicate rate, expired rate, source outcomes and static/browser split.

## Recommendation

Proceed with a focused **POC coverage and extraction-hardening slice** before any user-facing feed work:

1. fix Eden extraction semantics;
2. complete VisitMalta browser-mode validation;
3. qualify two more permitted Malta source classes;
4. execute the formal POC ingestion workflow;
5. only then evaluate the PRD's 14-day discovery-engine gates.

No production permission, scheduler activation, release approval or production enablement is implied by this report.
