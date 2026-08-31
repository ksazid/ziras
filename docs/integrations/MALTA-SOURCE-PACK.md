# Malta Source Pack

Status: VS-04 implementation baseline. Production source enablement is **not** approved.

## Why this exists

Ziras must not rediscover source/legal decisions every time a new adapter is added. The source pack turns vendor knowledge into machine-enforced policy plus replaceable adapter configuration.

The authoritative runtime catalog is:

`services/discovery/config/malta-source-policy.json`

## Policy scope

Each `SourcePolicy` now has an environment ceiling:

- `research` — qualification/live research only.
- `poc` — Malta proof-of-concept use is allowed, but not production release.
- `production` — technically eligible for production, still subject to release/production-enable gates.

A lower scope can never be silently promoted to a higher one.

## Policy controls

Each source records:

- access mode (`allow`, `deny`, `partner_only`, `user_share_only`)
- policy scope
- policy/terms URL
- review timestamp
- whether robots must be honored
- approved URL path prefixes
- maximum request rate
- attribution requirement
- whether raw page content may be stored

Defaults are intentionally conservative: robots required, attribution required, raw content storage disabled.

## Current vendor conclusions

### McDonald's Malta — DENY

Current online-service terms give a personal/non-commercial license and explicitly prohibit unauthorized automated systems such as spiders, robots and screen scrapers from accessing/extracting content.

### Pizza Hut Malta — DENY

Current terms state website copyright material may be reproduced only for personal, non-commercial use or internal organisational circulation. Ziras will not use website crawling as a commercial source without permission.

### Franks Malta — DENY

Current terms state the site is provided solely for personal use and may not be used for a commercial purpose.

### Wolt / Zara / Cloudigo — PARTNER ONLY

These remain API/affiliate/partner/licensed-feed candidates. There is no scraping fallback.

### Research/POC candidates

VisitMalta, Eden Cinemas, Homemate, Eurospin and Lidl are deliberately scoped below production. They are used only to prove source density and normalization quality under low-rate, robots-aware collection. Every one requires a fresh production review before a production scope can be granted.

## Live smoke runner

`services/discovery/scripts/live_source_smoke.py`

Properties:

- fixed URLs from the governed catalog
- policy-scope check before network access
- `robots.txt` check where required
- public-IP check
- cross-host redirect rejection
- response body cap
- one-shot low-rate behavior
- no credentials
- no login
- no browser stealth
- no raw page persistence
- emits only status, HTTP status, byte count, candidate count and content hash

Example:

```bash
python services/discovery/scripts/live_source_smoke.py --scope research
```

A source can also be targeted explicitly:

```bash
python services/discovery/scripts/live_source_smoke.py --scope research --source eurospin_promotions
```

## Acquisition dependencies

Production acquisition remains behind the ADR-001 ports. The package records these optional dependencies without forcing them into every kernel install:

- Scrapy `2.18.0`
- scrapy-playwright `0.0.48`
- Huey `3.3.4`

Static acquisition remains first choice. Browser rendering is fallback-only.

## Production enablement checklist

Before any source is promoted to `production` scope:

1. re-review current terms/API agreement;
2. confirm robots behavior for exact paths;
3. confirm factual fields and retention are permitted;
4. define attribution/deep-link behavior;
5. define request cadence and rate limits;
6. validate stale/expiry handling;
7. add source fixture regression tests;
8. run limited live smoke;
9. record policy approval;
10. obtain release + production-enable approval.

No source should be promoted because it merely worked technically.
