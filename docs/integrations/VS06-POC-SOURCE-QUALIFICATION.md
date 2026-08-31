# VS-06 Malta POC Source Qualification — 2026-08-31

Scope: POC policy evidence only. This document does not grant production source access.

## Decision rules

Every source remains fail-closed. POC `allow` means only the approved public path, at the recorded request cap, with robots enforcement, attribution and no raw-content/image retention. Production always requires a separate current review and approval.

## Approved for POC

### Spazju Kreattiv Events

- source key: `spazju_kreattiv_events`
- class: `cultural-venue-events`
- public listing: `https://spazjukreattiv.org/events/list/`
- current official inventory reviewed on 2026-08-31 includes Malta-local September/October 2026 events.
- reviewed official pages expose dates and venue/location facts suitable for deterministic event normalization.
- no blanket automated-access or non-commercial-use prohibition was located in the reviewed public policy material.
- runtime robots compliance remains mandatory.
- approved path: `/events/`
- maximum: 1 request/hour
- retained data: title/date/location/source URL/provenance only
- page bodies, event descriptions and images: not retained

Policy result: `allow`, scope `poc` only.

### Eurosport Malta Sale

- source key: `eurosport_malta_sale`
- class: `sports-retail`
- public listing: `https://www.eurosport.com.mt/sale`
- current Sale page reviewed on 2026-08-31 exposes deterministic old/new EUR prices across many products.
- Terms & Conditions: `https://www.eurosport.com.mt/conditions-of-use`
- Online Offers terms: `https://www.eurosport.com.mt/eurosport-online-offers-terms-and-conditions`
- reviewed terms govern goods/orders/offers; no blanket automated-access/non-commercial-use prohibition was located.
- runtime robots compliance remains mandatory.
- approved path: `/sale`
- maximum: 1 request/hour
- retained data: product name/current price/original price/source URL/provenance only
- no account, login, cart, wishlist or checkout access
- page bodies and images: not retained

Policy result: `allow`, scope `poc` only.

## Existing POC sources retained

1. `visitmalta_events` — `events-official`
2. `eden_cinemas` — `entertainment-offers`
3. `homemate_offers` — `home-retail`

Together with the two additions, VS-06 reaches five independent POC source classes.

## Explicitly not approved in this review

### Plaza Shopping Centre

Reviewed terms restrict content to personal/non-commercial use and restrict copying/storing without written consent. No automated POC source added.

### University of Malta

Reviewed authorized-use wording limits use to noncommercial/personal/educational purposes unless permission is obtained. No automated POC source added.

### Aggregator / competitor inventories

Cloudigo and similar third-party deal aggregators are not source inventory for scraping. Keep partner/licensed-feed only.

## Unchanged restricted sources

- McDonald's Malta — deny
- Pizza Hut Malta — deny
- Franks Malta — deny
- Wolt Malta — partner-only
- Zara Malta — partner-only
- Cloudigo Malta — partner-only
- Lidl Malta — research-only
- Eurospin Malta — research-only

VS-06 must not relax these states.

## Re-review conditions

Re-review any source before production, and immediately if terms, robots behavior, URL ownership, access controls or data presentation materially changes.
