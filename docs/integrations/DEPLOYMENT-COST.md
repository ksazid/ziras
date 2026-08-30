# Optional deployment-cost advisor

PES does not choose or enable a hosting provider by default. The deployment-cost advisor compares a reviewed workload profile with provider-fit rules and produces recommendations only.

## User-selectable topology

Edit `deployment/PROFILE.json` and choose one of:

- `single-provider` — frontend, API and database stay with one provider where technically supported.
- `split` — frontend, API and database may each use a different provider.
- `advisor-recommended` — PES compares both topologies and recommends the better fit.

The final selection must include the database and requires:

```json
{
  "approvedSelection": true
}
```

Human approval records the decision only. The advisor still cannot authenticate, provision infrastructure, create databases, modify DNS or deploy code.

## Use

```bash
npm run deployment:advise
```

The advisor compares application providers and database providers separately, then scores complete deployment topologies.

## Application adapters

- `cloudflare` — static assets, edge-compatible APIs and low-egress workloads
- `netlify` — frontend previews, static sites and supported web frameworks
- `vercel` — Next.js-focused delivery and pull-request previews
- `render` — containerized APIs, persistent services and background workers

## Database adapters

- `neon` — managed/serverless PostgreSQL
- `supabase` — managed PostgreSQL with optional platform services
- `render-postgres` — managed PostgreSQL alongside Render services
- `provider-managed-postgres` — generic same-provider option when available

These are guidance adapters, not provider SDK dependencies. Current pricing, plan limits, regions, backup support and production suitability must be verified before approval.

## Decision factors

The advisor considers:

- frontend, API and database runtime
- single-provider versus split operational complexity
- prototype, pilot or production stage
- commercial use
- expected traffic, connections and bandwidth
- cold-start tolerance
- preview deployment needs
- edge execution and background jobs
- connection pooling
- backups and point-in-time recovery
- regional and data-residency requirements
- stated monthly budget
- cross-provider egress and networking

## Coordinated release policy

Frontend, API and database are one release candidate even when hosted separately.

Required order:

```text
database and migrations
→ API deployment
→ API readiness and health verification
→ frontend deployment
→ frontend-to-API-to-database smoke test
→ release promotion
```

Rules:

- Frontend and API must reference the same certified Git SHA.
- Database migration identity must be recorded in release evidence.
- API deployment occurs before the frontend.
- CORS, authentication, secrets and API URLs must be validated across providers.
- Failure of any component fails the coordinated release.
- Frontend, API and database each need rollback instructions.
- Destructive migrations require an approved recovery strategy.

## Required verification

Before accepting a recommendation, verify current official provider documentation for:

- compute and function limits
- bandwidth, egress and cross-region transfer
- build minutes and preview usage
- database storage, connections and compute
- connection pooling and transaction constraints
- backups, restore tests and point-in-time recovery
- sleep, cold-start and availability behaviour
- regions and data residency
- commercial-use restrictions
- observability and log retention

## Governance

- Recommendations never enable a plugin automatically.
- Production deployment always requires human approval.
- The durable topology and provider selection should be recorded in an ADR.
- Exact-SHA certification and protected-environment release gates remain mandatory.
- Keep provider configuration removable; domain code must not depend directly on hosting vendors.
- Prefer one provider when cost and runtime fit are comparable; choose split deployment only when the benefit exceeds the added operational complexity.

## Adding an adapter

A new adapter must document:

1. supported runtimes and deployment model
2. known constraints and portability risks
3. cost drivers rather than hard-coded prices
4. security, secrets, rollback and observability expectations
5. backup and recovery behavior for database adapters
6. an uninstall or migration path
7. tests for its scoring rules

Do not merge an adapter whose main purpose is affiliate promotion or whose recommendation cannot be independently verified.
