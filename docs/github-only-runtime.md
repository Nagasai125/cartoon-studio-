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
- GitHub Actions runs orchestration and validation. Rendering and publishing
  will use separate credential boundaries when enabled.
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

## Workflow Checkpoints

`dry-run-episode.yml` executes the versioned state sequence from planning through
final validation. Every activity has a stable idempotency key, attempt limit,
deadline, simulated cost, input digest, and output digest. A checkpoint can be
resumed only from an explicitly selected prior workflow run and must match the
current episode and policy versions.

The checkpoint artifact replaces PostgreSQL and outbox semantics for this
GitHub-only pilot. It is immutable per workflow attempt, contains public-safe
metadata only, and expires after 30 days. The Pages snapshot is a projection and
is never accepted as workflow input.

The dry-run provider produces deterministic metadata without media or paid API
calls. Budget exhaustion and checkpoint tampering fail closed. The terminal
state is `needs_approval`; approval and publishing are unreachable from this
workflow.

`deploy-pages.yml` is a manual fallback for intentionally restoring the demo
dashboard. It does not run on code pushes or advance authoritative episode
state, so it cannot accidentally overwrite a workflow snapshot.

Provider calls, scheduled production, and YouTube publishing remain disabled
until their credentials and policies are configured.
