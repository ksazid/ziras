<p align="center">
  <img src="docs/assets/pes-overview.png" alt="Product Engineering Starter Overview" width="100%">
</p>

# Product Engineering Starter Mobile

An open-source governance layer for turning an approved **PRD** and **TRD** into a traceable, secure, cost-controlled web product.

Product Engineering Starter (PES) decides **what is approved and safe to build**. [Superpowers](https://github.com/obra/superpowers) provides the default methodology for planning, implementing, reviewing, debugging and finishing an approved slice.

## What PES provides

- PRD/TRD intake and conflict detection
- source-linked requirements and traceability
- roadmaps, milestones, epics and vertical slices
- architecture, design and security governance
- typed approvals, structured decisions and governed lifecycle transitions
- focused active-slice context and protected paths
- risk-based impact, ownership, release, rollback and post-release contracts
- Loop Engineering-inspired state, budgets, gates, run history and stop conditions
- deterministic preflight, certification evidence and exact-SHA release controls
- a generated read-only delivery dashboard with computed action notifications
- optional memory, knowledge, brevity, deployment and delivery-graph integrations
- human-controlled merge, release and production enablement

## Default mobile stack

- Next.js + TypeScript
- ASP.NET Core
- PostgreSQL + EF Core
- OpenAPI
- xUnit and Playwright
- Docker Compose
- GitHub Actions

## Mobile application baseline

- Expo SDK 57 / React Native 0.86 / React 19.2
- Expo Router and typed routes
- EAS development, preview and production build profiles
- SecureStore, Notifications, Updates, Localization and Network state
- TanStack Query and Zod
- Jest Expo and React Native Testing Library
- Android and iOS release gates bound to the exact certified SHA

The static `dashboard/` remains the read-only PES governance dashboard. It is not a web product application.

## Prerequisites

- Git 2.40+
- Node.js 24 LTS with npm
- .NET SDK 10.x
- Docker with Compose v2
- A supported coding-agent harness for Superpowers
- Optional: GitHub CLI, Python 3.9+, Codex Security, NotebookLM, MemPalace and Caveman

## Install

Use this repository as a GitHub template, or clone it directly:

```bash
git clone https://github.com/ksazid/product-engineering-starter.git my-product
cd my-product
npm install
npm run preflight:structure
npx expo install --fix --cwd apps/mobile
npm run preflight
```

## Start a product

1. Complete `product/PRD.md`.
2. Complete `product/TRD.md`.
3. Add design rules to `product/DESIGN.md`.
4. Define terminology in `product/GLOSSARY.md`.
5. Approve the source documents.
6. Run intake and planning.

```bash
npm run product:intake
npm run planning:generate
npm run planning:validate
npm run engineering:advise
```

The intake process blocks missing sections, unresolved draft status, conflicts and unsupported assumptions rather than inventing policy.

## Delivery workflow

```text
PRD + TRD
→ product, technical and security intake
→ source-linked requirements
→ roadmap, milestones, epics and vertical slices
→ typed scope and policy decisions
→ human plan and implementation approval
→ activate one vertical slice
→ focused context pack
→ Superpowers planning, TDD, implementation and review
→ deterministic preflight
→ risk-triggered security or delivery graph when justified
→ exact-SHA certification approval
→ release contract and rollback readiness
→ human release and production-enable approval
→ production verification
→ post-release outcome review
```

```bash
npm run slice:activate -- VS-01
npm run slice:status
npm run slice:transition -- implementing
npm run slice:validate
```

## End-to-end governance

PES records independent approval types for scope, policy, implementation, certification, release and production enablement. It also records product decisions and the exact gates each unresolved decision blocks.

The canonical lifecycle is:

```text
proposed
→ discovery
→ decision-pending
→ approved
→ ready-for-implementation
→ implementing
→ testing
→ certification
→ certified
→ release-pending
→ released
→ observed
→ validated
```

Exception states include `blocked`, `rejected`, `deferred`, `superseded` and `rolled-back`.

Implementation permission is explicit:

```text
specification-only
contracts-only
runtime-disabled
runtime-enabled
production-enabled
```

Run the governance validator:

```bash
npm run governance:validate
```

See `docs/governance/END-TO-END.md`.

## Delivery dashboard

PES includes a static read-only dashboard generated from the authoritative delivery files. It shows slice lifecycle, gate progress, approvals, pending decisions, blockers, certification, releases, rollback history and computed notifications.

```bash
npm run dashboard:build
npm run dashboard:serve
```

Open `http://127.0.0.1:4173`. GitHub Actions also uploads the generated dashboard as the `pes-dashboard` artifact.

The dashboard deliberately has no database, authentication or editable approvals. Repository files remain authoritative.

## Operating modes

PES begins in **Lite** mode and adds complexity only when evidence shows it will reduce risk or rework.

| Mode | Intended use | Delivery execution |
| --- | --- | --- |
| **Lite** | MVPs, solo developers and low-risk work | Single-agent Superpowers execution |
| **Standard** | Growing products, multiple modules and formal releases | Optional risk-triggered review graph |
| **Enterprise** | High-risk, regulated or multi-team products | Optional full specialist delivery graph |

### Why the delivery graph is not available in Lite

A graph adds routing, specialist hand-offs, integration and independent review calls. That increases token usage and coordination time. For routine CRUD, copy changes, isolated styling and low-risk maintenance, those costs usually exceed the value gained.

Standard and Enterprise make the graph available because medium- and high-risk changes can create much larger downstream costs when defects, security gaps or incompatible decisions are missed. Even in those modes, the graph is **not automatic**: a reviewed trigger and human approval are required for each slice.

## Risk-triggered delivery graph

### Standard review graph

```text
Approved slice
→ router
→ implementer
→ deterministic checks
→ reviewer
→ human checkpoint
```

Standard mode allows one specialist, one review cycle and no parallel execution by default.

### Enterprise delivery graph

```text
Approved slice
→ router
→ selected specialists
→ shared state
→ integrator
→ deterministic checks
→ independent reviewer
→ human checkpoint
```

Enterprise may select up to three roles from researcher, architect, security, data and builder, with at most two review cycles by default.

### Activation triggers

Typical triggers include:

- authentication or authorization
- payments or financial state
- sensitive data
- database migrations
- public API contract changes
- major architecture changes
- cross-module changes
- production release candidates
- repeated implementation failures

### Cost controls

The graph is designed to reduce total delivery cost, not merely add agents. PES requires:

- one focused context pack reused across nodes
- deterministic checks before model-backed review
- unchanged nodes skipped using input or commit hashes
- one integrator rather than all specialists rereading every output
- capped specialists, retries and review cycles
- budget-exceeded stop conditions
- token and outcome recording for later evaluation

The graph cannot change approved scope, accept security risk, merge code or deploy.

Check the active-mode configuration:

```bash
npm run delivery-graph:check
```

Configuration: `.engineering/DELIVERY-GRAPH.json`  
Guidance: `docs/integrations/DELIVERY-GRAPH.md`

## Responsibility boundary

| PES | Superpowers |
| --- | --- |
| Product and technical authority | Feature-level clarification |
| Requirement IDs and traceability | Implementation planning |
| Roadmap and vertical slices | Worktrees and execution |
| Typed approvals and decisions | No approval authority |
| Architecture and security policy | TDD and debugging |
| Protected paths and human gates | Spec and code-quality review |
| Preflight and certification | Branch completion workflow |
| Release and production approval | No release authority |

## Optional integrations

### NotebookLM

Use `npm run knowledge:export` to create a curated onboarding and Q&A bundle. GitHub remains authoritative. See `docs/integrations/NOTEBOOKLM.md`.

### MemPalace

Optional local-first memory for large requirements and long-running products. Retrieved memories must be verified against current Git sources.

```bash
uv tool install mempalace
npm run memory:doctor
mempalace init .
```

See `docs/integrations/MEMPALACE.md`.

### Caveman Lite

Optional concise communication and guarded context compression. Lite brevity is suitable for routine summaries, CI triage, commits and review comments—not PRDs, ADRs, security findings, plans or release evidence.

```bash
npm run optimize:context
```

See `docs/integrations/CAVEMAN.md`.

## Deployment strategy

PES treats frontend, API and database as one coordinated release, even when hosted by different providers.

Supported topology choices:

- **Advisor recommended** — PES recommends a topology; the user approves it.
- **Single provider** — frontend, API and database use one provider where supported.
- **Split deployment** — frontend, API and database use independently selected providers.

```bash
npm run deployment:advise
```

The advisor considers runtime compatibility, PostgreSQL requirements, traffic, bandwidth, cold starts, previews, background jobs, regions, recovery, cross-provider complexity and budget. It never provisions or deploys infrastructure.

Release order:

```text
Certified SHA
→ database readiness and migrations
→ API deployment and health checks
→ frontend deployment
→ end-to-end smoke tests
→ human production approval
```

See `docs/integrations/DEPLOYMENT-COST.md`.

## UI workflow

Use the approved design baseline first, then only relevant installed skills:

1. Taste Skill for suitable marketing, editorial and approved redesign work.
2. UI UX Pro Max for product workflows, accessibility and responsive states.
3. Impeccable for bounded polish.
4. Emil design engineering for purposeful motion.
5. Ponytail for maintainable implementation.
6. Superpowers for planning, implementation and review.

## Security model

Use deterministic secret scanning, dependency validation, authorization tests, security headers and protected-path rules. Codex Security remains optional and risk-triggered for authentication, authorization, payments, uploads, webhooks, sensitive persistence, migrations and release candidates.

## Main commands

```bash
npm run product:intake
npm run planning:generate
npm run planning:validate
npm run governance:validate
npm run slice:activate -- VS-01
npm run slice:transition -- <state>
npm run slice:status
npm run slice:validate
npm run delivery:status
npm run dashboard:build
npm run dashboard:serve
npm run delivery-graph:check
npm run deployment:advise
npm run security:classify -- <changed-files>
npm run knowledge:export
npm run memory:doctor
npm run optimize:context
npm run preflight
npm run certify
npm run engineering:advise
npm run profile:show
```

## Large requirements

Parse the whole product once, plan broadly at release and milestone level, detail only the next milestone and execute only the active slice. Use focused context packs under `delivery/context/<slice-id>/`; MemPalace may retrieve historical context, but Git remains authoritative.

```text
Product → Release → Milestone → Epic → Vertical Slice → Context Retrieval → Superpowers Plan → Task
```

## Deliberate exclusions

No Kubernetes default, microservice generation, event-sourcing default, generic repositories, uncontrolled agent swarms, autonomous merge, autonomous production deployment, general-purpose project-management system, mandatory hosting provider or mandatory Ruflo dependency.

## License

MIT — see [LICENSE](LICENSE).


## npm registry troubleshooting

This open-source starter uses the public npm registry through the repository `.npmrc`. If an organization overrides npm with a private mirror, that mirror must proxy scoped packages such as `@types/react`. Verify with:

```bash
npm config get registry
npm install
npm run preflight:structure
npx expo install --fix --cwd apps/mobile
```

PES does not vendor JavaScript dependencies into the repository.
