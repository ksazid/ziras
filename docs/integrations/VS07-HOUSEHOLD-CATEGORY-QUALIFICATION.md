# VS-07 Malta Household-Value Category Qualification

Status: **POC-ONLY — Day 1 hardening under fresh certification; production not approved**

The product owner approved seven household-value categories for the Malta POC:

1. Grocery & supermarket
2. Restaurant / takeaway
3. Family & kids
4. Activities
5. Senior discounts
6. Pharmacy / personal care
7. Spa & wellness

## Global policy rules

- Public factual metadata only.
- Exact configured paths and rate caps only.
- robots.txt remains mandatory.
- No login/account/cart/checkout/booking/payment/customer-data crawling.
- No CAPTCHA bypass, anti-bot bypass, stealth/proxy rotation or browser impersonation to defeat technical controls.
- No raw page/image/creative retention.
- Attribution/provenance is required.
- HTTP success with zero expected inventory fails closed where `minimum_candidates=1` is configured.
- Production always requires a separate fresh review and explicit approval.

## Grocery — Lidl Malta public offers

- key: `lidl_malta_poc_offers`
- class: `supermarket`
- public path: `https://www.lidl.com.mt/c/`
- fetch: static
- rate: 1/hour
- POC-only; original `lidl_malta_offers` remains research-only.

Decision: **POC allowed** for narrow factual offer metadata.

## Restaurant / takeaway — AX Hotels Sliema direct offers

- key: `ax_sliema_dining_offers`
- class: `restaurant-direct`
- selected Victoria/The Palace direct offer-detail URLs only
- fetch: static
- rate: max 4/hour
- no booking/payment paths.

Day 1 finding: the broad extractor repeated related-site offers on each detail page, causing 45 duplicates. The approved corrective boundary treats the direct page H1 as the page's authoritative discovery and ignores related-offer rails/site-wide structured inventory.

Decision: **POC allowed with detail-page extraction boundary**.

## Family & kids — Esplora promotions

- key: `esplora_family_promotions`
- class: `family-kids`
- path: `https://esplora.org.mt/promotions-tcs/`
- fetch: static
- rate: 1/hour.

Decision: **POC allowed** for public family-promotion facts. Generic numbered headings such as `Promotion 1:` are noise; descriptive headings remain eligible.

## Activities — Heritage Malta What's On

- key: `heritage_malta_activities`
- class: `activities-official`
- path: `https://heritagemalta.mt/whats-on/`
- fetch: static
- rate: 1/hour
- no shop/cart access.

Decision: **POC allowed** for official event/activity metadata.

## Senior discounts — Day 1 amendment

### Active Ageing and Community Care

- key: `active_ageing_discounts`
- class: `senior-benefits-official`
- path: `https://aacc.gov.mt/en/discounts-for-the-elderly/`
- Day 1 automated POC acquisition returned **HTTP 403**.

Ziras will not alter user agents, use proxies, browser impersonation or another technique to bypass that observed technical restriction.

Decision: **demoted to research/reference scope; POC automated acquisition denied** pending a permitted machine-access route or partnership.

### GO Malta Kartanzjan offers

- key: `go_kartanzjan_offers`
- class: `senior-benefits-direct`
- public path: `https://www.go.com.mt/offers/kartanzjan/`
- fetch: static
- rate: 1/hour
- public factual 60+ Kartanzjan offer metadata only
- no application form, MyGO/login, account, checkout or customer-data paths.

Decision: **POC replacement allowed**, robots-governed, production denied pending fresh review.

A Servizz.gov automated replacement was not adopted because its published terms prohibit page-scrape/robot/automatic acquisition/monitoring.

## Pharmacy / personal care — Botika Malta sale

- key: `botika_personal_care_sale`
- class: `pharmacy-personal-care`
- path: `https://botika.mt/collections/sale`
- fetch: static
- rate: 1/hour
- no login/cart/checkout.

Decision: **POC allowed** for public product title/current/original price metadata.

## Spa & wellness — AX Verdala direct offer

- key: `ax_verdala_wellness_offers`
- class: `spa-wellness`
- path: `https://axhotelsmalta.com/verdala-wellness/special-offers/leisure/day-by-the-pool/`
- fetch: static
- rate: 1/hour
- no booking/payment paths.

Day 1 finding: the previous broad wellness + gift-voucher pages generated 24 duplicates and CTA/FAQ/navigation noise. The POC is therefore narrowed to a current direct offer-detail page and the same detail-page H1 extraction boundary used for AX dining.

Decision: **POC allowed on the narrowed direct path**.

## Existing restrictions unchanged

- McDonald's Malta — deny.
- Pizza Hut Malta — deny.
- Franks Malta — deny.
- Wolt Malta — partner-only.
- Deal.mt — reference/validation only.
- Corinthia — automated acquisition not approved because reviewed terms prohibit robot/spider/automatic monitoring without prior consent.
- Servizz.gov — not used for automated acquisition because reviewed terms prohibit scrape/robot/automatic access/monitoring.

## Approval and certification state

- Original seven-category expansion: product-owner approved 2026-08-31.
- Day 1 corrective policy/implementation batch: product-owner approved with **“Go ahead”** on 2026-09-01.
- Day 1 amendment still requires fresh exact-head PES, regression, PostgreSQL and live acquisition evidence before certification/merge.
- Production source access: **OFF / NOT APPROVED**.
- Release/production enablement: **NOT APPROVED**.
