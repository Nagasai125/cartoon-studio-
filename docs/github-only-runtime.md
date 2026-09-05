# GitHub-Only Runtime

## Decision

Cartoon Studio uses GitHub as its only application infrastructure. The earlier
cloud-service design remains a reference, but it is not the active deployment
target.

## Runtime

```text
  push or manual dispatch
            |
            v
  GitHub Actions runner
  |-- validate code
  |-- run the production state machine
  |-- create public-safe dashboard.json
  |-- build the dashboard
  `-- deploy the Pages artifact
            |
            v
       GitHub Pages
```

- GitHub Pages serves the dashboard and public-safe status snapshots.
- GitHub Actions runs orchestration, validation, rendering, and publishing.
- GitHub Secrets stores provider and YouTube credentials.
- GitHub Environments provides the final owner approval gate.
- Workflow artifacts retain non-sensitive reports and status history only.
- The local FastAPI, PostgreSQL, and MinIO stack remains available for
  development but is not a production dependency.

## Media Boundary

This repository and its Pages site are public. Workflows must not publish
prompts, credentials, private source material, or unpublished media as Pages,
logs, caches, releases, or artifacts.

Future production runs will render in the runner's temporary workspace and
upload the final file directly to YouTube with `private` visibility. The owner
reviews that private upload. A separate environment-protected workflow may make
the exact approved YouTube video public after validating its recorded hash and
video ID.

## Current Milestone

`deploy-pages.yml` exports a typed simulation snapshot, archives that public-safe
JSON for 30 days, builds the dashboard, and deploys it. Manual runs can advance
the simulation to exercise each dashboard state without a backend.

Provider calls, scheduled production, and YouTube publishing remain disabled
until their credentials and policies are configured.
