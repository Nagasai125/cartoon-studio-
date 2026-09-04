# Deployment Architecture

## Purpose

This document defines local, staging, and production topology, cloud resources,
configuration, scaling, backup, and rollback.

## Deployment Baseline

| Capability | Baseline |
| --- | --- |
| Static frontend | GitHub Pages |
| API | Google Cloud Run service |
| Worker | Google Cloud Run service or job, based on activity |
| Schedule | Google Cloud Scheduler |
| Task delivery | Google Cloud Tasks |
| Secrets | Google Secret Manager |
| Database | Supabase managed PostgreSQL with pgvector |
| Authentication | Supabase Auth with GitHub OAuth |
| Media | Supabase private object storage |
| AI generation | External provider APIs |
| Container registry | Google Artifact Registry |
| Logging and metrics | Cloud Logging/Monitoring plus OpenTelemetry |

Provider substitutions are permitted when they preserve the interfaces and
security boundaries in this design.

## Production Topology

```text
  Internet
     |
     +--> dashboard.example.com
     |        |
     |        v
     |    GitHub Pages
     |
     +--> api.example.com
              |
              v
        +-------------+
        | Cloud Run   |
        | API         |
        +------+------+                 +----------------+
               |                        | Cloud Scheduler|
               |                        +-------+--------+
               |                                |
               v                                v
        +-------------+                  schedule route
        | Supabase    |                         |
        | DB/Auth/    |<------------------------+
        | Storage     |
        +------+------+
               |
               | outbox
               v
        +-------------+
        | Cloud Tasks |
        +------+------+
               |
               v
        +-------------+       +-------------------+
        | Cloud Run   |------>| External AI APIs  |
        | worker      |       +-------------------+
        +------+------+
               |
               v
        Supabase storage
```

## Local Environment

Local development uses Docker Compose for dependencies:

```text
  Developer machine
  |
  |-- Vite dashboard dev server
  |-- FastAPI with reload
  |-- Python worker
  |-- PostgreSQL + pgvector container
  |-- MinIO-compatible storage container
  |-- fake task dispatcher
  `-- fake deterministic AI providers
```

Local development must not require paid provider credentials. Optional sandbox
credentials are loaded from an ignored local environment file.

## Environment Isolation

| Resource | Local | Staging | Production |
| --- | --- | --- | --- |
| Database | Container | Dedicated project | Dedicated project |
| Storage | Local object store | Dedicated buckets | Dedicated buckets |
| OAuth | Local callback | Staging OAuth app | Production OAuth app |
| API | Local | Staging Cloud Run | Production Cloud Run |
| Queue | Fake/local adapter | Staging queue | Production queue |
| Providers | Fake/sandbox | Sandbox/limited | Production keys |
| YouTube | Disabled/fake | Private test upload | Production channel |

No credentials, databases, buckets, queues, or callbacks are shared across
staging and production.

## Cloud Run Services

### API Service

- Public HTTPS ingress
- Authentication enforced by application
- Minimum instances initially zero unless cold-start data says otherwise
- Concurrency tuned for I/O requests
- No FFmpeg rendering in request handlers
- Read-only container filesystem except temporary working directory
- Non-root process
- Health and readiness endpoints

### Worker Service

- Authenticated ingress only
- Cloud Tasks service identity required
- Lower request concurrency for media work
- Explicit memory, CPU, and timeout per task class
- Temporary files deleted after upload
- No publishing credentials

### Render Job

Use a Cloud Run Job for work exceeding ordinary HTTP worker characteristics.
The job receives only IDs, fetches inputs from private storage, writes outputs,
and reports completion to the API.

## Configuration

Configuration categories:

| Category | Storage |
| --- | --- |
| Public frontend API URL | GitHub Actions build variable |
| Non-secret runtime flags | Cloud Run environment variables |
| Provider keys | Secret Manager |
| YouTube token | Isolated Secret Manager secret |
| Policy and budgets | Versioned PostgreSQL records |
| Infrastructure IDs | OpenTofu state and deployment outputs |

No secret is prefixed with `VITE_` or embedded in the static dashboard.

## Domains and TLS

Recommended production domains:

```text
  dashboard.example.com  -> GitHub Pages
  api.example.com        -> Cloud Run/API gateway mapping
```

Use HTTPS only. Configure exact production and staging origins separately.

GitHub Pages does not provide full custom security-header control. The static
shell therefore contains no private data. If stronger header control becomes a
requirement, move the same Vite output to a compatible static host.

## Scaling

Initial workload is three episodes weekly. Default scaling should optimize for
low idle cost rather than high constant throughput.

Scale in this order:

1. Increase queue concurrency within provider and budget limits.
2. Increase worker maximum instances.
3. Separate render and ingestion worker profiles.
4. Introduce self-hosted GPU worker adapters.
5. Extract a service only when runtime or security boundaries require it.

## Self-Hosted Model Extension

Future GPU workers implement existing provider contracts:

```text
  Production worker
         |
         v
  Provider router
      |       |
      |       +--> managed API adapter
      |
      +----------> self-hosted GPU adapter
                         |
                         v
                    GPU job service
```

The dashboard, episode state machine, database schema, and approval model remain
unchanged.

## Deployment Rollback

### Frontend

Redeploy the previous successful Pages artifact or commit. Frontend rollback
must remain compatible with the currently deployed API version.

### API and Worker

Cloud Run retains immutable revisions. Shift traffic to the previous image
digest after confirming database compatibility.

### Database

Prefer forward correction. A down migration is used only when explicitly tested
and data-safe. Destructive migrations require backup and restoration planning.

## Backup and Disaster Recovery

- Managed PostgreSQL point-in-time recovery
- Object storage versioning where supported
- Nightly essential metadata export
- Monthly restoration exercise
- Infrastructure reproducible from OpenTofu and documented bootstrap steps
- Recovery runbook for YouTube tokens and OAuth configuration

Initial objectives:

| Measure | Objective |
| --- | --- |
| Database recovery point | Provider-supported point-in-time recovery |
| Control-plane recovery time | Four hours |
| Static dashboard recovery | One hour |
| Lost approved publication records | Zero |

## Cost Controls

- Scale API and workers to zero when practical.
- Apply maximum Cloud Run instances.
- Apply queue dispatch limits.
- Reserve episode budgets before paid operations.
- Alert at monthly budget percentages.
- Use media lifecycle rules for unused candidates.
- Record confirmed provider cost whenever available.
- Do not optimize infrastructure cost at the expense of approval or audit
  guarantees.
