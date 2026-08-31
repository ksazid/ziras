# VS-06 Malta POC Source Qualification — 2026-08-31

Status: **QUALIFIED CANDIDATES — POLICY APPROVAL PENDING**

This document records source-policy evidence and a recommendation. It does not itself authorize acquisition or change source access mode/scope.

## Decision rules

- Every source remains fail-closed until an explicit policy approval is recorded.
- POC approval, if granted, applies only to the named public path/API, request cap, attribution and retention constraints.
- Production always requires a separate current review and approval.
- No login/account/cart access, anti-bot bypass, proxy rotation, CAPTCHA bypass or raw creative/image retention is allowed.

## Recommended immediate POC candidates

### Candidate A — Spazju Kreattiv Events

- proposed source key: `spazju_kreattiv_events`
- proposed class: `cultural-venue-events`
- public event inventory: official Spazju Kreattiv site, Valletta
- proposed acquisition: static web, robots mandatory
- proposed path: `/events/`
- proposed rate cap: 1 request/hour
- proposed retained facts: event title, date/time, venue/location, source URL and provenance
- page body, long descriptions and images: not retained

Evidence reviewed on 2026-08-31:

- official site exposes current Malta-local events and future dates;
- event detail pages expose deterministic date/location facts;
- no blanket automated-access prohibition was located in the reviewed public policy material;
- absence of a prohibition is not treated as production permission, therefore this recommendation is POC-only and low-rate.

**Policy confidence:** medium.  
**Inventory confidence:** high.  
**Recommendation:** approve for low-rate POC factual metadata only, or keep disabled if a stricter explicit-license standard is preferred.

### Candidate B — Eurosport Malta Sale

- proposed source key: `eurosport_malta_sale`
- proposed class: `sports-retail`
- public listing: `https://www.eurosport.com.mt/sale`
- proposed acquisition: static web, robots mandatory
- proposed path: `/sale`
- proposed rate cap: 1 request/hour
- proposed retained facts: product name, current price, original price, source URL and provenance
- no account, login, cart, wishlist or checkout access
- page body and images: not retained

Evidence reviewed on 2026-08-31:

- the public Sale page exposes many deterministic old/new EUR prices;
- published Terms & Conditions primarily govern sale of goods;
- Online Offers terms govern specific discounts/offers;
- no blanket automated-access prohibition was located in the reviewed terms;
- this is still not a production license, so the recommendation is intentionally narrow and POC-only.

**Policy confidence:** medium.  
**Inventory confidence:** high.  
**Recommendation:** approve for low-rate POC factual sale metadata only, or keep disabled if a stricter explicit-license standard is preferred.

## Stronger-license alternatives

### MALRO open cultural-event API

MALRO explicitly describes its event database as open, downloadable and API-queryable. Its public API is GET-only/no-auth, and its material is generally CC BY 4.0 with rate-limit obligations; images are excluded from that open-content treatment.

**Policy confidence:** high.  
**Malta inventory confidence:** not yet sufficient to count it toward the Malta five-source gate.  
**Recommendation:** keep as a high-quality API candidate; do not count toward the gate until useful Malta inventory is demonstrated.

### Ticketmaster Discovery API

The official Discovery API supports country code `MT`, event search and structured event/venue data. It requires an API key. Ticketmaster's API terms restrict storage/caching, replication of the Ticketmaster experience and commercial use outside permitted cases.

**Policy confidence:** high when used under the API terms.  
**Inventory confidence:** requires credential-backed Malta smoke query.  
**Operational dependency:** API key.  
**Recommendation:** good later API source; not the fastest fifth POC source until credentials and a Malta inventory smoke test are available.

## Existing POC sources retained

1. `visitmalta_events` — `events-official`
2. `eden_cinemas` — `entertainment-offers`
3. `homemate_offers` — `home-retail`

Current explicitly approved count remains **3 independent POC source classes**.

## Explicitly not promoted

- McDonald's Malta — deny
- Pizza Hut Malta — deny
- Franks Malta — deny
- Wolt Malta — partner-only
- Zara Malta — partner-only
- Cloudigo Malta — partner-only
- Lidl Malta — research-only
- Eurospin Malta — research-only

## Required approval before runtime addition

A separate explicit source-policy approval must name the candidate(s) and approve the proposed POC constraints. Until then:

- the runtime catalog remains at 3 approved POC source classes;
- no request is sent to either candidate by Ziras;
- the PRD `>=5 independent source types` gate remains unmet.
