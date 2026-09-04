# System Architecture

## Purpose

This document defines the system context, deployable components, boundaries,
and runtime communication patterns.

## System Context

```text
                      +----------------------+
                      | Owner                |
                      | operates and approves|
                      +----------+-----------+
                                 |
                                 v
                      +----------------------+
                      | Cartoon Studio       |
                      +---+---------+--------+
                          |         |
             source fetch |         | generation requests
                          v         v
                 +------------+  +----------------+
                 | Approved   |  | AI providers   |
                 | sources    |  +----------------+
                 +------------+          |
                                           | results/callbacks
                                           v
                                +----------------------+
                                | Cartoon Studio       |
                                +----------+-----------+
                                           |
                                           | approved publication
                                           v
                                +----------------------+
                                | YouTube              |
                                +----------------------+
```

## Deployable Components

### Dashboard

Static React application deployed to GitHub Pages.

Responsibilities:

- Authenticate the owner.
- Query the API.
- Display production, knowledge, assets, cost, and QA.
- Receive live event updates.
- Submit commands such as pause, retry, approve, and reject.

The dashboard contains no business authority. Hiding or disabling a button is
not authorization.

### Control API

FastAPI application deployed as a managed container.

Responsibilities:

- Validate identity and authorization.
- Expose versioned HTTP APIs.
- Enforce domain transitions and approval invariants.
- Query PostgreSQL and issue signed media URLs.
- Create jobs and outbox entries transactionally.
- Receive authenticated provider callbacks.
- Expose the live event stream.
- Invoke publishing only after independent approval verification.

### Production Worker

Python worker deployed from the same image as the API with a different process
entry point.

Responsibilities:

- Claim authenticated task deliveries.
- Run knowledge ingestion and validation.
- Call AI providers through internal adapters.
- Process images, audio, and video.
- Build deterministic 2D compositions.
- Run FFmpeg and media validation.
- Store immutable artifacts and normalized results.
- Emit events and schedule follow-up work.

### Database

Managed PostgreSQL with `pgvector`.

Responsibilities:

- Authoritative episode and workflow state.
- Knowledge, asset, rights, cost, and approval metadata.
- Full-text and semantic indexes.
- Transactional outbox and append-only event records.
- Audit history.

### Object Storage

Private managed object storage.

Responsibilities:

- Immutable source snapshots.
- Original and derived assets.
- Scene outputs, audio, captions, and final renders.
- Episode manifests and QA artifacts.
- Short-lived signed read access.

### Task Delivery

Managed HTTP task queue.

Responsibilities:

- Deliver jobs to workers.
- Apply queue-level concurrency and rate limits.
- Retry transient delivery failures.
- Authenticate worker requests.

The task queue is not authoritative. A task without a valid database job record
does nothing.

## Runtime Topology

```text
  Browser
     |
     | HTTPS API and SSE
     v
  +--------------------+          +--------------------+
  | API container      |--------->| PostgreSQL         |
  +---------+----------+          +---------+----------+
            |                               |
            | signed media URL              | metadata
            v                               |
  +--------------------+                    |
  | Private storage    |                    |
  +--------------------+                    |
                                            |
  +--------------------+                    |
  | Cloud Scheduler    |                    |
  +---------+----------+                    |
            |                               |
            v                               |
  +--------------------+                    |
  | API schedule route |                    |
  +---------+----------+                    |
            |                               |
            | outbox                        |
            v                               |
  +--------------------+                    |
  | Cloud Tasks        |                    |
  +---------+----------+                    |
            | authenticated HTTP            |
            v                               |
  +--------------------+                    |
  | Worker container   |<-------------------+
  +----+-----------+---+
       |           |
       v           v
  AI providers   storage
```

## Public and Private Boundaries

| Surface | Exposure | Protection |
| --- | --- | --- |
| GitHub Pages files | Public | No secrets or private content included |
| API | Public HTTPS | OAuth token, authorization, rate limit, CORS |
| SSE endpoint | Public HTTPS | Same authentication as API |
| Provider callbacks | Public HTTPS | Signature, timestamp, nonce, job match |
| Worker endpoint | Private/authenticated | Cloud Tasks service identity |
| Database | Private managed connection | Service identity and TLS |
| Object storage | Private | Signed URLs and service identity |
| Publisher | Backend-only command | Approval hash and owner authorization |

## API Boundary

The API is versioned at `/api/v1`.

Primary resources:

```text
/auth
/dashboard
/episodes
/episode-versions
/scenes
/workflow-runs
/jobs
/events/stream
/knowledge/sources
/knowledge/search
/assets
/licenses
/qa
/approvals
/providers
/budgets
/settings
/publishing
```

FastAPI produces OpenAPI. CI generates and verifies a TypeScript client for the
dashboard. The frontend does not hand-write duplicate response types.

## Communication Rules

- Browser-to-API communication uses JSON over HTTPS.
- Live activity uses Server-Sent Events with polling fallback.
- Worker payloads contain IDs and object URLs, not large binaries.
- Provider calls have explicit connect, read, and total timeouts.
- Provider callbacks are normalized before entering domain logic.
- Internal events are append-only and include correlation identifiers.
- Commands use idempotency keys.
- All timestamps are UTC and serialized as RFC 3339.

## Modular Monolith Boundaries

```text
  packages/pipeline/
  |
  |-- domain          entities, values, invariants
  |-- workflows       states, transitions, activities
  |-- providers       external AI and publishing adapters
  |-- knowledge       ingestion, retrieval, citations
  |-- media           assets, composition, rendering
  |-- validation      policy and QA checks
  `-- publishing      approval verification and upload
```

Modules communicate through explicit Python interfaces. They may share a
database transaction through application services, but one module does not
reach into another module's private tables or provider implementation.

## Provider Adapter Contract

Every provider adapter returns a normalized result containing:

- Internal job ID
- Provider job ID
- Provider and model identifier
- Model revision when available
- Request and response hashes
- Normalized usage
- Estimated or confirmed cost
- Artifact references
- Safety metadata
- Start and completion timestamps
- Retry classification on failure

Provider-specific JSON is retained for audit but does not drive business logic.

## Rendering Boundary

The renderer accepts a versioned scene timeline and approved asset references.
It does not decide educational content or rewrite scenes.

```text
  Scene specification
         |
         +--> approved SVG/PNG assets
         +--> character rig and poses
         +--> dialogue and timing
         +--> captions and text
         +--> transitions and camera cues
         |
         v
  Deterministic timeline renderer
         |
         v
  image sequence / intermediate video
         |
         v
  FFmpeg assembly and validation
         |
         v
  immutable final render
```

## Scaling Boundaries

Scale vertically and through worker concurrency before splitting services.

Consider extracting a service only when one of these is measured:

- A component needs an incompatible runtime or GPU image.
- Independent scaling materially lowers cost.
- A security boundary requires separate credentials.
- Deployment frequency creates operational conflict.
- A module has a separate owner and stable API.

Do not split services solely because the domain has multiple named agents.
