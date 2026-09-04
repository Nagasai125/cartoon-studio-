# CI/CD Architecture

## Purpose

This document defines repository standards, GitHub Actions, GitHub Pages,
backend deployment, migrations, security checks, releases, and rollback.

## Repository Strategy

Use one private monorepo with trunk-based development.

```text
  feature branch
       |
       v
  pull request
       |
       v
  required CI checks
       |
       v
  merge to main
       |
       +--------------------> deploy GitHub Pages
       |
       +--------------------> build and deploy staging backend
                                    |
                                    v
                               smoke tests
                                    |
                                    v
                          protected production deploy
```

## Branch and Repository Rules

- Protect `main` with a GitHub ruleset.
- Require pull requests.
- Require passing status checks.
- Require linear history.
- Block force pushes and branch deletion.
- Permit the single owner to merge after checks pass.
- Enable secret scanning and push protection where available.
- Enable Dependabot security updates.
- Keep `CODEOWNERS` even with one owner.
- Do not use `pull_request_target` with untrusted code.

## Workflow Inventory

```text
  .github/workflows/
  |-- ci.yml
  |-- deploy-pages.yml
  |-- deploy-backend.yml
  |-- migrate.yml
  |-- security.yml
  |-- nightly.yml
  `-- release.yml
```

## `ci.yml`

Triggers:

- Pull requests
- Pushes to `main`

Frontend jobs:

- Install from lockfile
- Lint
- Type-check
- Unit and component tests
- Build production bundle
- Verify generated API client is current
- Run critical Playwright flows with fake backend
- Upload test and screenshot artifacts on failure

Backend jobs:

- Install from lockfile
- Ruff formatting and linting
- Pyright strict type check
- Pytest unit tests
- Integration tests with PostgreSQL and object storage
- Alembic migration upgrade tests
- OpenAPI schema generation and compatibility check

Workflow jobs:

- State transition tests
- Idempotency and duplicate-delivery tests
- Retry and budget tests
- Hash-bound approval tests
- Provider contract fixtures

No paid AI provider call runs in pull-request CI.

## GitHub Pages Deployment

`deploy-pages.yml` runs only for a successful trusted `main` revision.

```text
  checkout exact commit
          |
          v
  install locked dependencies
          |
          v
  test and build Vite
          |
          v
  configure Pages
          |
          v
  upload apps/dashboard/dist only
          |
          v
  deploy to github-pages environment
          |
          v
  HTTP smoke test
```

Minimum job permissions:

```yaml
permissions:
  contents: read
  pages: write
  id-token: write
```

Use the official actions:

- `actions/configure-pages`
- `actions/upload-pages-artifact`
- `actions/deploy-pages`

Pin each action to a reviewed full commit SHA. Dependabot proposes updates.

### Vite Base Path

Use `/` for a custom domain. Use `/<repository-name>/` for a project Pages URL.
The build receives this as non-secret configuration.

Use hash routing initially because GitHub Pages does not provide a normal SPA
fallback for direct navigation.

### Pages Environment

The deployment job uses the `github-pages` environment and reports the deployed
URL. Concurrency permits one active Pages deployment and cancels superseded
deployments.

The Pages artifact contains only static dashboard output. It does not contain
environment files, source documents, media, source maps, or backend secrets.

## Backend Deployment

`deploy-backend.yml` uses GitHub OIDC to obtain short-lived cloud credentials.
No static cloud deployment key is stored in GitHub.

```text
  successful main CI
          |
          v
  build OCI image once
          |
          +--> generate SBOM
          +--> vulnerability scan
          +--> keyless image signature
          |
          v
  push immutable image to Artifact Registry
          |
          v
  deploy same digest to staging API and worker
          |
          v
  staging smoke and workflow tests
          |
          v
  owner authorizes production environment
          |
          v
  deploy same digest to production
          |
          v
  production smoke test and revision record
```

Build once and promote the same digest. Do not rebuild for production.

## Database Migrations

`migrate.yml` is explicit and environment-protected.

Rules:

- Application startup never applies migrations.
- CI tests upgrade from an empty database and previous fixture.
- Staging migration runs before staging deployment verification.
- Production migration requires owner authorization.
- Expand schema before deploying code that uses it.
- Contract or remove schema only after old code is no longer deployed.
- Record migration revision in deployment metadata.

## Security Workflow

`security.yml` performs:

- CodeQL analysis
- Dependency review on pull requests
- Secret scanning integration
- Python and JavaScript dependency audit
- Container vulnerability scan
- Infrastructure static analysis
- License inventory

Findings above the accepted severity fail the workflow unless an expiring,
documented exception exists.

## Nightly Workflow

`nightly.yml` performs work that is too slow or expensive for every pull request:

- Controlled provider API smoke tests
- Callback contract checks
- Small end-to-end sandbox episode
- Source freshness checks
- Dependency and container refresh scan
- Database backup visibility check

Nightly provider work has a dedicated low budget and cannot publish.

## Release Workflow

`release.yml` runs for signed version tags.

It records:

- Git commit
- Dashboard artifact hash
- Container image digest and signature
- Database migration revision
- OpenAPI version
- Workflow definition version
- Release notes

Use semantic versioning for application releases. Episode and asset versions
remain domain versions and are independent of application releases.

## Action Security

- Default workflow permissions are read-only.
- Grant write permissions only to the job requiring them.
- Pin third-party actions to full commit SHA.
- Use OIDC for cloud access.
- Restrict OIDC trust by repository, environment, branch, and workflow.
- Do not expose secrets to forked pull requests.
- Avoid executing generated shell from provider or source content.
- Set job and command timeouts.
- Set artifact retention explicitly.

## Deployment Verification

Frontend smoke checks:

- Page returns success.
- Static assets load from the configured base path.
- Login action reaches the expected authentication origin.
- API health is reachable from the browser origin.

Backend smoke checks:

- Liveness and readiness succeed.
- Database query succeeds.
- Storage signing succeeds without exposing the service key.
- Queue enqueue and authenticated worker delivery succeed.
- Publishing remains disabled in staging.

## Rollback

### Dashboard

Redeploy the previous successful commit or retained Pages artifact.

### API and Worker

Shift Cloud Run traffic to the previous immutable revision and image digest.

### Database

Prefer a forward repair migration. Restore only for severe incidents with an
approved recovery procedure.

## Required Status Checks

Recommended required checks:

```text
  frontend-lint-type-test
  frontend-build
  backend-lint-type-test
  integration-test
  workflow-invariants
  migration-test
  security-baseline
```

CI names should remain stable because branch protection references them.
