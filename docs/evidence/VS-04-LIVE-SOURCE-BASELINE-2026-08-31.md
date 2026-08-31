# VS-04 Live Source Usefulness Baseline — 2026-08-31

Status: research evidence only. This document does **not** approve automated collection for any source.

## Purpose

Before enabling any production source, verify that the source actually carries discovery signals valuable to Ziras. This baseline records current public evidence separately from source permission.

## Findings

### VisitMalta Events

- Official source: `https://www.visitmalta.com/en/events-in-malta-and-gozo/`
- Sitemap: `https://www.visitmalta.com/en/sitemap.html`
- Observed: dated Malta/Gozo event listings, event categories, ticket/more-info actions and future event windows.
- Ziras value: `EVENT`, local activity, family/culture/nightlife/sports discovery.
- Policy state: `review_required` / candidate registry `DENY`.
- Why not enabled: public usefulness and search-engine sitemap availability do not by themselves establish production automated-collection permission.

### Deal.com.mt

- Official source: `https://deal.com.mt/`
- Observed: substantial live Malta deal inventory across food, hotels/getaways, activities, spa/wellness and other categories; public pages expose discount/value signals.
- Site also exposes a partner path.
- Ziras value: high-density `DEAL` evidence with strong local relevance.
- Policy state: `partner_required` / candidate registry `DENY`.
- Preferred enablement: approved partner/feed/API route or explicit automated-access permission, then a reviewed `PARTNER_ONLY` SourcePolicy.

### Decathlon Malta

- Official source: `https://www.decathlon.mt/`
- Sale page: `https://www.decathlon.mt/5430-sale`
- Observed: large sale catalogue with current price, price before reduction, discount percentage, and the lowest price in the previous 30 days on visible items.
- Ziras value: unusually strong deterministic `PRICE_DROP` / `DEAL` evidence and price-history context.
- Policy state: `review_required` / candidate registry `DENY`.
- Important implementation note: if schema.org data does not expose the former/30-day price, a later source-specific deterministic adapter may be justified after policy approval.

### SCAN Malta

- Official source: `https://www.scanmalta.com/`
- Observed: ecommerce product catalogues and special-price vs regular-price values on indexed product/search pages.
- Ziras value: technology `DEAL`, `PRICE_DROP`, `NEW_PRODUCT`, availability signals.
- Policy state: `review_required` / candidate registry `DENY`.

### Greens Supermarket

- Official source: `https://www.greens.com.mt/`
- Observed: active ecommerce operation and supermarket inventory/promotion capability.
- Ziras value: grocery/household promotion, price and availability discoveries.
- Policy state: `review_required` / candidate registry `DENY`.

### The Atrium Malta

- Official source: `https://www.theatrium.com.mt/`
- Observed: stock inventory is linked to the website; public retail catalogue and sale/offer pages are available.
- Public sale evidence includes substantial discount promotions across home categories.
- Ziras value: retail `DEAL`, `PRICE_DROP`, stock-back/new-product signals.
- Policy state: `review_required` / candidate registry `DENY`.
- Validation correction: the canonical domain is `theatrium.com.mt`; VS-04 profile was corrected before certification.

### Pizza Hut Malta

- Official source: `https://www.pizzahut.com.mt/`
- Deals page: `https://www.pizzahut.com.mt/categories/deals`
- Observed: multiple named deal/combo products with current prices and descriptions.
- Ziras value: restaurant `DEAL`, menu/promotion discoveries.
- Policy state: `review_required` / candidate registry `DENY`.

### ShowsHappening

- Official source: `https://www.showshappening.com/`
- Observed: dense Malta event calendar with dates, categories and ticket prices; many future events are publicly discoverable.
- Ziras value: `EVENT` inventory across nightlife, music, culture, education and experiences.
- Policy state: `partner_required` / candidate registry `DENY`.
- Preferred enablement: official partnership/feed/API route; a `partner=True` runtime flag alone never grants access.

## Coverage assessment

The combined source pack now has useful candidate inventory across four non-Meta discovery families:

1. events/ticketing;
2. dedicated deals;
3. retail/supermarket product and price signals;
4. restaurant/menu promotions.

Meta Ad Library adds a fifth independent source family through its official API path.

This is enough source diversity to proceed with source-by-source policy qualification without redesigning the engine.

## Next evidence gate

For each source that receives policy approval:

1. run a controlled live smoke test;
2. record static-vs-browser acquisition behavior;
3. measure structured normalization success;
4. measure discoveries/page and discoveries/day;
5. verify explicit expiry/price validity where available;
6. resolve entities/locations;
7. measure duplicate/stale/invalid-on-open rates;
8. only then request production-enable approval.
