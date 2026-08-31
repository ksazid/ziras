# VS-06 Malta POC Source Qualification — 2026-08-31

Status: **APPROVED FOR POC — PRODUCTION NOT APPROVED**

This document records the qualification evidence and the product owner's explicit SourcePolicy approval for the two named candidates below. Approval is limited to the exact POC constraints recorded here and in `malta-source-vs06-poc.json`.

## Decision rules

- POC approval applies only to the named public path, request cap, attribution and retention constraints.
- Production always requires a separate current review and approval.
- No login/account/cart access, anti-bot bypass, proxy rotation, CAPTCHA bypass or raw creative/image retention is allowed.
- The certified VS-04 policy baseline remains unchanged; VS-06 permissions are additive and separately auditable.

## Approved POC source A — Spazju Kreattiv Events

- source key: `spazju_kreattiv_events`
- class: `cultural-venue-events`
- public inventory: `https://spazjukreattiv.org/events/list/`
- acquisition: static web, robots mandatory
- allowed path: `/events/list/`
- rate cap: 1 request/hour
- retained facts: event title, date/time, venue/location, source URL and provenance
- page body, long descriptions and images: not retained
- policy evidence: `https://spazjukreattiv.org/privacy-policy/`

Evidence reviewed on 2026-08-31:

- the official site exposes current and future Malta-local events with deterministic date/location facts;
- no blanket automated-access prohibition was located in the reviewed public policy material;
- approval is intentionally low-rate and POC-only; it is not a production license.

**Policy confidence:** medium.  
**Inventory confidence:** high.  
**Decision:** APPROVED for the constraints above.

## Approved POC source B — Eurosport Malta Sale

- source key: `eurosport_malta_sale`
- class: `sports-retail`
- public listing: `https://www.eurosport.com.mt/sale`
- acquisition: static web, robots mandatory
- allowed path: `/sale`
- rate cap: 1 request/hour
- retained facts: product name, current price, original price, source URL and provenance
- no account, login, cart, wishlist or checkout access
- page body and images: not retained
- policy evidence: `https://www.eurosport.com.mt/conditions-of-use`

Evidence reviewed on 2026-08-31:

- the public Sale page exposes deterministic sale inventory and EUR pricing;
- published conditions primarily govern sale of goods and no blanket automated-access prohibition was located in the reviewed terms;
- approval is intentionally low-rate and POC-only; it is not a production license.

**Policy confidence:** medium.  
**Inventory confidence:** high.  
**Decision:** APPROVED for the constraints above.

## Existing POC sources retained

1. `visitmalta_events` — `events-official`
2. `eden_cinemas` — `entertainment-offers`
3. `homemate_offers` — `home-retail`
4. `spazju_kreattiv_events` — `cultural-venue-events`
5. `eurosport_malta_sale` — `sports-retail`

Approved count: **5 independent POC source classes**.

This satisfies the source-coverage prerequisite for the formal POC metrics run. It does **not** by itself satisfy the PRD's discoveries/day, validity, stale, duplicate or relevance thresholds.

## Stronger-license alternatives retained for later

### MALRO open cultural-event API

MALRO explicitly describes its event database as open, downloadable and API-queryable. Its public API is GET-only/no-auth, and its material is generally CC BY 4.0 with rate-limit obligations; images are excluded from that open-content treatment.

Keep as a high-confidence API candidate; do not count it toward current Malta coverage until useful Malta inventory is demonstrated.

### Ticketmaster Discovery API

The official Discovery API supports country code `MT`, event search and structured event/venue data. It requires an API key and carries caching/commercial-use constraints.

Keep as a later credential-backed source candidate.

## Explicitly not promoted

- McDonald's Malta — deny
- Pizza Hut Malta — deny
- Franks Malta — deny
- Wolt Malta — partner-only
- Zara Malta — partner-only
- Cloudigo Malta — partner-only
- Lidl Malta — research-only
- Eurospin Malta — research-only

## Approval record

Product owner approval: **Approved**  
Date: **2026-08-31**  
Scope: `spazju_kreattiv_events` and `eurosport_malta_sale` only, POC constraints above.  
Production source access: **NOT APPROVED**.
