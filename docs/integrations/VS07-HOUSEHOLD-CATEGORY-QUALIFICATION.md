# VS-07 Malta Household-Value Category Qualification — 2026-08-31

Status: **APPROVED FOR POC — PRODUCTION NOT APPROVED**

Product owner approved expanding the formal Malta POC before Day 1 with seven household-value categories:

1. Grocery & supermarket
2. Restaurant / takeaway
3. Family & kids
4. Activities
5. Senior discounts
6. Pharmacy / personal care
7. Spa & wellness

The existing five certified source classes remain unchanged. This document records the additive source-policy qualification for the seven categories above.

## Decision rules

- POC approval is limited to public factual metadata and the exact paths/rate caps recorded in configuration.
- Production always requires a separate current review and approval.
- No login/account/cart/checkout access, CAPTCHA/anti-bot bypass, stealth/proxy rotation, raw creative retention or image retention.
- robots.txt remains mandatory for web sources; if robots denies a path, acquisition must fail closed.
- Store only factual discovery fields such as title, price/discount, validity dates, location where available, source URL and provenance.
- Deal aggregators are not promoted merely because they have useful inventory; source-policy permission still controls acquisition.

## P0 — Grocery & supermarket

### Lidl Malta public offers

- source key: `lidl_malta_offers`
- class: `supermarket`
- public inventory: `https://www.lidl.com.mt/c/`
- acquisition: static web; robots mandatory
- allowed path: `/c/`
- rate cap: 1 request/hour
- retained facts: product title, current/original price or percentage saving, offer validity, source URL/provenance
- no Lidl Plus account, personalised coupons, search/account paths or CAPTCHA-protected areas
- policy evidence: public offers pages + Lidl terms/privacy material reviewed 2026-08-31

Evidence reviewed:
- public offer pages expose current weekly Malta inventory with explicit EUR prices, savings and validity dates;
- robots allows the reviewed `/c/` content path while disallowing specific search/technical paths;
- reviewed public material did not establish permission for broad commercial reuse, so approval remains narrow, low-rate and POC-only.

**Policy confidence:** medium.  
**Inventory confidence:** high.  
**Decision:** APPROVED for POC factual offer metadata only.

## P0 — Restaurant / takeaway

### AX Hotels Sliema dining offers

- source key: `ax_sliema_dining_offers`
- class: `restaurant-direct`
- public paths: selected current AX The Palace / AX The Victoria restaurant offer pages
- acquisition: static web; robots mandatory
- rate cap: 4 requests/hour
- retained facts: offer title, price/discount, validity text, venue/source URL and provenance
- no booking/payment paths
- policy evidence: AX public offer pages and published offer terms reviewed 2026-08-31

Evidence reviewed:
- current Summer 2026 direct offers expose deterministic prices and conditions, including Penny Sundays, Fish & Chips, Sweet Duo and Taco Thursdays;
- no blanket automated-access prohibition was located in reviewed public offer/policy material;
- approval is limited to exact public offer paths and factual metadata.

**Policy confidence:** medium.  
**Inventory confidence:** high.  
**Decision:** APPROVED for POC.

## P1 — Family & kids

### Esplora family promotions

- source key: `esplora_family_promotions`
- class: `family-kids`
- public inventory: `https://esplora.org.mt/promotions-tcs/`
- acquisition: static web; robots mandatory
- allowed path: `/promotions-tcs/`
- rate cap: 1 request/hour
- retained facts: promotion title, qualifying spend/value, family entitlement, source URL/provenance
- policy evidence: official Esplora promotions and privacy/public policy pages reviewed 2026-08-31

Evidence reviewed:
- official promotion page exposes family-specific benefits including free family admission tied to qualifying purchases;
- no blanket automated-access prohibition was located in reviewed public policy material;
- government/public-interest source, but POC still remains low-rate and factual-only.

**Policy confidence:** medium-high.  
**Inventory confidence:** medium.  
**Decision:** APPROVED for POC.

## P0/P1 — Activities

### Heritage Malta What's On

- source key: `heritage_malta_activities`
- class: `activities-official`
- public inventory: `https://heritagemalta.mt/whats-on/`
- acquisition: static web; robots mandatory
- allowed path: `/whats-on/`
- rate cap: 1 request/hour
- retained facts: event/activity title, date/time, price where available, venue/location, source URL/provenance
- policy evidence: Heritage Malta What's On + Terms & Conditions reviewed 2026-08-31

Evidence reviewed:
- official agency inventory currently lists 2026 activities/events and family programmes with dates, locations and ticket prices;
- Terms govern use/purchases and copyright; no blanket automated-monitoring prohibition was located in the reviewed terms;
- no shop/cart crawling is permitted by this approval.

**Policy confidence:** medium-high.  
**Inventory confidence:** high.  
**Decision:** APPROVED for POC.

## P1 — Senior discounts

### Active Ageing and Community Care — Discounts for the Elderly

- source key: `active_ageing_discounts`
- class: `senior-benefits-official`
- public inventory: `https://aacc.gov.mt/en/discounts-for-the-elderly/`
- acquisition: static web; robots mandatory
- allowed path: `/en/discounts-for-the-elderly/`
- rate cap: 1 request/hour
- retained facts: participating business, discount/benefit, locality/address where published, source URL/provenance
- policy evidence: official Government of Malta programme page reviewed 2026-08-31

Evidence reviewed:
- the official programme publishes 60+ benefits covering supermarkets, restaurants, transport, eyewear, leisure and other services;
- examples in the POC geography include Sliema, Gżira, St Julian's, Birkirkara and Valletta;
- no account/login or personal-data collection is required to read the public list.

**Policy confidence:** high.  
**Inventory confidence:** high.  
**Decision:** APPROVED for POC.

## P1 — Pharmacy / personal care

### Botika Malta Sale

- source key: `botika_personal_care_sale`
- class: `pharmacy-personal-care`
- public inventory: `https://botika.mt/collections/sale`
- acquisition: static web; robots mandatory
- allowed path: `/collections/sale`
- rate cap: 1 request/hour
- retained facts: product title, current/original price, source URL/provenance
- no login, cart or checkout access
- policy evidence: Botika public sale collection and published terms/privacy material reviewed 2026-08-31

Evidence reviewed:
- the public sale collection exposes health, beauty, skincare, wellness, baby-care and personal-care products with old/current EUR prices;
- reviewed public terms/privacy material did not expose a blanket automated-access prohibition;
- only public sale-listing facts are approved; no customer/account data or checkout behaviour.

**Policy confidence:** medium.  
**Inventory confidence:** high.  
**Decision:** APPROVED for POC.

## P1 — Spa & wellness

### AX Verdala wellness offers

- source key: `ax_verdala_wellness_offers`
- class: `spa-wellness`
- public inventory: selected Verdala/AX public wellness and gift-voucher pages
- acquisition: static web; robots mandatory
- rate cap: 2 requests/hour
- retained facts: experience/package title, price/discount, validity where published, source URL/provenance
- no booking/payment paths
- policy evidence: AX public wellness/gift-voucher pages and published voucher conditions reviewed 2026-08-31

Evidence reviewed:
- public pages expose concrete wellness experiences such as V SPA day passes and wellness-retreat products with published EUR pricing;
- reviewed AX public material did not expose a blanket automated-monitoring prohibition;
- approval is low-rate, factual-only and excludes booking/payment flows.

**Policy confidence:** medium.  
**Inventory confidence:** medium-high.  
**Decision:** APPROVED for POC.

## Explicit non-promotion decisions

- Deal.mt — useful validation/reference inventory, but not promoted to automated POC acquisition in this batch.
- Corinthia public offer pages — **not approved** for automated POC acquisition because published Corinthia terms explicitly prohibit robot/spider/automatic monitoring/copying without prior express consent.
- McDonald's Malta — deny unchanged.
- Pizza Hut Malta — deny unchanged.
- Wolt Malta — partner-only unchanged.
- Franks Malta — deny unchanged.

## Combined POC value stack after this batch

### Core household value
1. Grocery & supermarket
2. Restaurant / takeaway
3. Events & activities
4. Family & kids
5. Senior discounts
6. Pharmacy / personal care
7. Spa & wellness

### Existing supporting classes retained
- home retail
- sports retail
- entertainment offers
- cultural venue events

This expansion occurs before the formal Day 1 measurement run. It does not itself prove any 14-day PRD success metric.

## Approval record

Product owner approval: **Approved — “lets add these”**  
Date: **2026-08-31**  
Scope: seven household-value POC categories above only.  
Production source access: **NOT APPROVED**.  
Release/production enablement: **NOT APPROVED**.
