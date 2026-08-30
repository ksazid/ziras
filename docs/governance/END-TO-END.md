# End-to-End Product Governance

PES keeps Git files authoritative and adds machine-enforced governance without introducing a workflow server, database or autonomous approval system.

## What changed

The delivery model now records:

- typed approvals rather than a generic “approved” state;
- product and policy decisions with explicit blocking effects;
- one canonical lifecycle for each slice;
- the maximum implementation permission currently granted;
- risk-based impact declarations and accountable owners;
- exact-SHA certification and release contracts;
- rollback readiness and immutable rollback records;
- post-release outcomes, metrics and review dates;
- a generated read-only dashboard and computed notifications.

These structures extend the existing slice, checklist, PR and certification workflow. They do not replace the PRD, TRD, ADRs, specifications, tests, GitHub reviews or human authority.

## Authoritative files

| File | Purpose |
| --- | --- |
| `delivery/governance.json` | Allowed states, approval types, modes, risk levels and transitions |
| `delivery/current-slice.json` | Active slice and its full governance state |
| `delivery/backlog.json` | Planned slices using the same governed slice shape |
| `delivery/completed-slices.json` | Completed, rejected, superseded or rolled-back slice records |
| `delivery/decisions.json` | Append-oriented product and policy decisions |
| `delivery/releases.json` | Exact-SHA release contracts and production verification |
| `delivery/rollbacks.json` | Rollback or forward-recovery execution history |

Markdown remains the human-readable explanation. JSON is the machine-readable status used by validation and the dashboard.

## Typed approvals

PES recognises six independent approval types:

1. `scope` — the slice boundary and exclusions are accepted;
2. `policy` — product, legal, financial or operational policy values are accepted;
3. `implementation` — the allowed implementation boundary may proceed;
4. `certification` — evidence for an exact commit SHA is accepted;
5. `release` — the certified SHA may enter the release process;
6. `production-enable` — disabled or guarded production behaviour may be enabled.

An approval must record its status, approver, timestamp, rationale and either a document version or exact commit SHA. Certification, release and production enablement approvals always require a 40-character commit SHA.

Approval status values are:

```text
pending
approved
rejected
changes-requested
revoked
not-required
```

Approvals are not interchangeable. Scope approval does not authorise runtime implementation, and release approval does not authorise production enablement when that behaviour has a separate safety gate.

## Decision registry

Each decision has a stable `DEC-<number>` identifier and may block one or more gates:

```json
{
  "id": "DEC-01",
  "sliceId": "VS-16",
  "question": "Which cancellation fee applies inside 30 days?",
  "status": "pending",
  "options": ["No fee", "Fixed fee", "Percentage fee"],
  "decision": null,
  "ownerRole": "product-owner",
  "rationale": null,
  "decidedBy": null,
  "decidedAt": null,
  "blocks": ["implementation", "release", "production-enable"]
}
```

Pending or changes-requested decisions block only the targets listed in `blocks`. This permits safe specification, contract or disabled-runtime work while preventing invented production policy.

## Slice lifecycle

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

Exception and terminal states are:

```text
blocked
rejected
deferred
superseded
rolled-back
```

Allowed transitions are defined in `delivery/governance.json` and enforced by:

```bash
npm run slice:transition -- <state>
```

The command rejects invalid transitions and restores the previous state when the target state violates approval, decision, certification or release rules.

## Implementation permission levels

A slice records the maximum implementation permission currently granted:

| Mode | Meaning |
| --- | --- |
| `specification-only` | Documents and planning only |
| `contracts-only` | Interfaces, schemas and disabled contracts only |
| `runtime-disabled` | Runtime may be implemented but must remain fail-closed or disabled |
| `runtime-enabled` | Runtime may be exercised outside production under approved scope |
| `production-enabled` | Explicitly approved production behaviour may be enabled |

`production-enabled` requires a production-enable approval. Runtime modes require scope and implementation approval.

## Risk and impact

Every slice declares `low`, `medium` or `high` risk and lists affected areas such as API, database, authorization, payments, sensitive data, customer flow, operator flow, privacy, deployment and operational support.

Medium-risk slices require product and engineering owners plus an impact declaration. High-risk slices additionally require operations and security owners. Medium and high-risk releases require rollback readiness.

This applies stronger controls where failure cost is high without adding the same ceremony to copy, styling or isolated low-risk changes.

## Release contract

A release record binds deployment to one exact commit SHA and records:

- included slices;
- migrations;
- configuration changes;
- feature flags;
- smoke tests;
- rollback or forward-recovery strategy;
- human approval;
- production verification.

A release cannot be recorded as released until production verification passes. Deployment completion alone is not release success.

## Rollback contract

Rollback records are append-oriented and retain:

- the affected release;
- reason;
- initiator and timestamp;
- status;
- verification evidence.

A completed rollback requires verification evidence. Previous approvals and release records are not overwritten.

## Post-release validation

Released slices must declare:

- expected customer or business outcome;
- at least one metric;
- a review date;
- post-release status.

The post-release loop is:

```text
released → observing → validated | iterate | rollback-required
```

This connects delivered software to product learning without claiming that process controls can guarantee market success.

## Validation

Run:

```bash
npm run governance:validate
npm run preflight
```

Validation fails for unsafe contradictions, including:

- runtime work without scope and implementation approval;
- production enablement without explicit approval;
- blocked decisions being bypassed;
- certification approval not matching the certified SHA;
- release before certification;
- medium/high-risk release without rollback readiness;
- released slices without an outcome review contract.

Advisory inconsistencies are emitted as warnings rather than blockers.

## Dashboard

Build and open the read-only dashboard:

```bash
npm run dashboard:build
npm run dashboard:serve
```

The dashboard displays:

- portfolio totals and governed progress;
- lifecycle and gate progress for each slice;
- approvals, decisions and blockers;
- exact-SHA certification and release status;
- rollback history;
- computed action-required notifications.

The first version deliberately has no login, editable approvals, persistent notification database or external messaging. Repository files remain the source of truth.
