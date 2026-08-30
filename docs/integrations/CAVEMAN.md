# Caveman integration (optional)

Caveman is an optional communication and context-compression integration. It is disabled by default. When enabled, use **lite** mode unless a team explicitly approves a stricter level.

## Recommended uses

- Status updates
- CI triage summaries
- Commit messages
- Pull-request review comments
- Routine run summaries

## Do not use brevity mode for

- PRD/TRD analysis
- Architecture decisions or ADR rationale
- Security findings or accepted-risk decisions
- Acceptance criteria
- Implementation plans that require exact detail
- Certification and release evidence
- User-facing or public documentation

## Install

Follow the upstream instructions for the coding-agent harness in use. A common skills-registry command is:

```bash
npx skills add JuliusBrussee/caveman
```

After installation, enable `lite` mode in the agent session. Caveman remains external to PES and is not installed by `npm install`.

## Context compression

Run a guarded preview:

```bash
npm run optimize:context
```

The preview lists eligible files and protected exclusions. It does not alter files.

After installing `caveman-compress`, explicitly apply compression:

```bash
PES_CONTEXT_COMPRESSION_APPROVED=1 npm run optimize:context -- --apply
```

On PowerShell:

```powershell
$env:PES_CONTEXT_COMPRESSION_APPROVED='1'; npm run optimize:context -- --apply
```

The wrapper creates timestamped backups under `.engineering/backups/context/`, invokes `caveman-compress` one file at a time, and stops on failure.

## Eligible by default

- `AGENTS.md`
- Internal workflow and routing guides selected by the wrapper

## Permanently excluded

- `product/PRD.md`
- `product/TRD.md`
- ADRs
- Security policies and findings
- API/OpenAPI contracts
- Release and certification evidence
- `README.md`
- Source code, tests, migrations, and configuration containing product semantics

Every compressed change requires normal diff review, preflight, and human approval. Compression must preserve commands, paths, identifiers, policy meaning, and authority order.
