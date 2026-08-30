# Progressive operating modes

The starter begins in **Lite mode**. More governance is recommended only when repository evidence shows that it will reduce risk or rework.

## Lite — default

Use for MVPs and small teams. Includes intake, planning, vertical slices, Superpowers single-agent execution, deterministic preflight, baseline security and human review.

The delivery graph is deliberately unavailable in Lite. Routing, specialist hand-offs, integration and independent review add model calls and coordination overhead that routine low-risk work usually cannot justify.

Lite supports optional NotebookLM knowledge export, MemPalace local memory, Caveman Lite and deployment-cost guidance. These remain disabled by default.

## Standard — growing product

Adds ADR governance, threat modelling, evidence bundles, complete certification and an optional **risk-triggered review graph**:

```text
router → implementer → deterministic checks → reviewer → human checkpoint
```

Use it only for medium-risk work where an independent review is likely to prevent meaningful rework. It permits one specialist, one review cycle and no parallel execution by default.

## Enterprise — high-risk or multi-team product

Adds maker/checker execution, worktrees, budgets, risk-triggered Codex Security and an optional **full delivery graph**:

```text
router → selected specialists → integrator → deterministic checks → independent reviewer → human checkpoint
```

The graph is suitable for authentication, payments, sensitive data, migrations, public API changes, major architecture changes, cross-module work and release candidates. Default limits are three specialists and two review cycles.

## Why graph execution is restricted

A delivery graph increases input context, coordination output and review calls. It is cost-effective only when the expected reduction in defects, missed risk or rework exceeds that extra agent cost.

PES therefore reuses one focused context pack, runs deterministic checks first, skips unchanged nodes by hash, uses one integrator, caps specialists and retries, records usage and stops when the budget is exceeded.

Being in Standard or Enterprise mode does not activate the graph automatically. A reviewed trigger and human approval are required for each active slice.

Check the current configuration with:

```bash
npm run delivery-graph:check
```

See `docs/integrations/DELIVERY-GRAPH.md` and `.engineering/DELIVERY-GRAPH.json`.

## Growth advisor

```bash
npm run engineering:advise
```

The advisor reads repository evidence and recommends capabilities. It never changes the mode, installs a plugin, modifies product policy or enables autonomous execution.

## Adoption rule

A capability must satisfy all of the following before it is enabled:

1. A recurring problem or material risk is measured.
2. The capability addresses that problem directly.
3. Its expected benefit exceeds maintenance and agent-credit cost.
4. A human approves the change.
5. The change can be removed without restructuring the product.
