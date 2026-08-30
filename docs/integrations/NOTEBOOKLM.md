# NotebookLM integration (optional)

NotebookLM is an optional team-learning and onboarding layer for Product Engineering Starter (PES). It is not a runtime dependency and never becomes a source of truth.

## Authority rule

GitHub remains authoritative for PRDs, TRDs, ADRs, security decisions, active slices, skills, code, certification evidence, and release state. NotebookLM may explain and summarize those materials, but its answers must not override them.

Use this notice in every shared notebook:

> GitHub is authoritative. NotebookLM answers are explanatory summaries and must not override repository documents, approved decisions, current code, or release evidence.

## Export a curated knowledge bundle

```bash
npm run knowledge:export
```

The command writes `dist/knowledge/` with curated Markdown sources and `SOURCE-MANIFEST.json`, including the repository commit SHA, export timestamp, source paths, and content hashes.

Recommended notebook name:

```text
Product Engineering Starter — Team Guide
```

Upload only the generated bundle. Refresh it after material changes to governance, architecture, security, operating modes, or delivery workflow.

## Good uses

- New-developer onboarding
- PES versus Superpowers explanations
- Workflow and operating-mode Q&A
- Architecture and security summaries
- Contributor FAQs, study guides, and audio overviews

## Do not use it for

- Approving requirements or decisions
- Determining current implementation state without checking GitHub
- Security-risk acceptance
- Release certification or deployment authority
- Replacing code review, tests, or repository evidence

## Data handling

Do not export secrets, credentials, private customer data, production logs, sensitive security findings, or restricted documents. Review the generated bundle before sharing it outside the repository team.
