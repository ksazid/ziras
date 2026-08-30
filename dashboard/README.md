# PES Delivery Dashboard

This directory contains a static, read-only dashboard generated from the authoritative files under `delivery/`.

## Use

```bash
npm run dashboard:build
npm run dashboard:serve
```

Open `http://127.0.0.1:4173`.

`dashboard:build` refreshes `data.json`. The UI uses no framework, database, authentication or remote service. GitHub Actions also builds and uploads the directory as the `pes-dashboard` artifact.

## Notifications

Notifications are derived from current repository state. They are not separately persisted. The dashboard surfaces:

- pending, rejected, revoked or changes-requested approvals;
- pending decisions and the gates they block;
- slice blockers;
- failed or stale certification;
- scheduled post-release reviews.

Interactive approvals and read/unread notification state remain intentionally deferred until PES is used by multiple authenticated users or projects.
