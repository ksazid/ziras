# MemPalace integration

MemPalace is an optional local-first memory layer for long-running PES projects. It stores source material and prior conversations verbatim, then retrieves relevant context through semantic search.

## Authority boundary

MemPalace is retrieval support, not a source of truth.

Authority remains, in order:

1. Approved PRD and TRD
2. Approved security decisions and ADRs
3. Approved design baseline and delivery plan
4. Active vertical slice
5. Current repository code and tests

A retrieved memory must never override a newer authoritative repository file. When memory and Git disagree, Git wins and the stale memory should be refreshed.

## Best use cases

- Large PRDs and TRDs
- Long-running products
- Architecture rationale and prior discussions
- Decision continuity across agent sessions
- Focused context retrieval for an active slice
- Team onboarding and historical questions

Do not use MemPalace to approve requirements, accept security risk, certify a release, or authorize deployment.

## Installation

Install the CLI in an isolated Python environment. The upstream project recommends `uv tool`:

```bash
uv tool install mempalace
mempalace init .
```

`pipx install mempalace` is also supported. MemPalace requires Python 3.9 or later and uses a local ChromaDB backend by default. Its core path requires no API key.

## Suggested PES workflow

```bash
# Index stable project documents and selected discussion exports
mempalace mine product/
mempalace mine docs/
mempalace mine .engineering/

# Retrieve relevant historical context
mempalace search "why was this authentication approach selected"

# Load remembered context when beginning a new session
mempalace wake-up
```

Exclude secrets, local environment files, credentials, private customer data, production dumps, and sensitive document content.

## Context rule

Use retrieval to construct a small context pack for the active slice. Do not inject the entire memory store into every agent turn.

Recommended sequence:

```text
Active slice
→ search MemPalace for relevant decisions
→ verify results against current Git files
→ include only supported excerpts in the context pack
→ execute with Superpowers
```

## Storage choices

The default embedded ChromaDB backend is recommended for individual developers and small teams because it has no hosted-service bill. Server backends such as Qdrant, pgvector, and Milvus should remain opt-in and be adopted only when shared or centralized memory is genuinely required.

## Privacy and retention

- Prefer local storage.
- Never index secrets or regulated personal data by default.
- Define retention and deletion rules before sharing a central memory backend.
- Treat retrieved conversations as potentially stale.
- Record the current Git commit SHA in generated context or evidence where practical.

## Verification

Run:

```bash
npm run memory:doctor
```

This checks whether the MemPalace CLI is available and prints the safe initialization path. It does not install software or index repository content automatically.
