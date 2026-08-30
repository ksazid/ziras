# Risk-triggered delivery graph

The delivery graph adds coordinated specialist execution to PES for work where the expected reduction in defects and rework can justify additional model calls.

## Availability

- **Lite:** unavailable. Routine and low-risk slices use one focused Superpowers execution path because routing, specialist hand-offs and independent review usually cost more than they save.
- **Standard:** optional lightweight review graph for medium-risk slices.
- **Enterprise:** optional full delivery graph for high-risk, cross-cutting or release-critical slices.

The graph is never activated merely because a project is in Standard or Enterprise mode. A reviewed trigger and human approval are still required.

## Standard graph

```text
Approved slice
→ router
→ implementer
→ deterministic checks
→ reviewer
→ human checkpoint
```

Standard mode permits one specialist and one review cycle. Parallel execution is disabled by default.

## Enterprise graph

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

Available specialist roles include researcher, architect, security, data and builder. The default configuration caps execution at three specialists and two review cycles.

## Activation triggers

Examples include authentication or authorization, payments, sensitive data, database migrations, public API contract changes, major architecture changes, cross-module changes, production release candidates and repeated failed implementation attempts.

Routine CRUD, copy changes, isolated styling and low-risk maintenance should remain single-agent unless evidence shows otherwise.

## Cost effectiveness

The graph adds input context, coordination output and review calls. It is cost-effective only when the expected cost of defects, rework or missed risk is higher than the additional agent cost.

PES therefore requires:

- one focused context pack reused by all nodes
- deterministic checks before model-backed review
- unchanged nodes skipped using input or commit hashes
- one integrator rather than every specialist rereading all outputs
- capped specialists, retries and review cycles
- budget-exceeded stop conditions
- token and outcome recording for later evaluation

## Authority and safety

The delivery graph cannot change approved scope, accept security risk, merge code or deploy. PRDs, TRDs, ADRs, security decisions, the active slice and human approvals remain authoritative.

## Check configuration

```bash
npm run delivery-graph:check
```

The command reports whether the graph is available for the active mode and lists its limits and triggers. It does not activate agents or perform implementation.

Configuration lives in `.engineering/DELIVERY-GRAPH.json`.
