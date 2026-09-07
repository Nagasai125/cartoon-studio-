# Data Architecture

## Purpose

This document defines authoritative records, relationships, versioning,
storage, search, migrations, retention, and recovery.

## Active GitHub-Only Data Principles

- Versioned checkpoint artifacts are authoritative for active pilot runs.
- Checkpoints contain metadata and hashes only; unpublished media is never an
  Actions artifact.
- Each resume names an exact prior workflow run and validates the checkpoint,
  episode, definition, policy, and digest chain.
- The GitHub Pages snapshot is a read-only projection and never workflow input.
- PostgreSQL and object storage below are inactive scaling references.

## Cloud-Ready Reference Principles

- PostgreSQL is authoritative for metadata and state.
- Object storage is authoritative for large immutable artifacts.
- Queues and caches are reconstructable delivery mechanisms.
- Approved and cited records are never overwritten.
- Every external artifact has a checksum.
- Query-critical fields use relational columns, not opaque JSON.
- Provider-specific details may use JSON but remain isolated.

## Logical Relationship Model

```text
  SERIES 1 -------- * EPISODE 1 -------- * EPISODE_VERSION
                                                |
                                                +---- * SCENE
                                                |       |
                                                |       +---- * SCENE_VERSION
                                                |
                                                +---- * WORKFLOW_RUN
                                                |       |
                                                |       +---- * JOB
                                                |               |
                                                |               +---- * JOB_ATTEMPT
                                                |
                                                +---- * QA_RESULT
                                                +---- * APPROVAL
                                                +---- * CITATION
                                                +---- * ASSET_USAGE

  KNOWLEDGE_SOURCE 1 ---- * SOURCE_SNAPSHOT 1 ---- * KNOWLEDGE_CHUNK
                                                         |
                                                         +---- * EMBEDDING
                                                         +---- * CITATION

  ASSET 1 -------- * ASSET_VERSION 1 -------- * ASSET_USAGE
                           |
                           +---- 1 LICENSE
```

## Production Tables

### `series`

Stores original series identity, audience, language, visual bible, and active
policy references.

### `episodes`

Stores stable episode identity, scheduling, learning objective, and lifecycle.

### `episode_versions`

Stores immutable revisions of brief, script, storyboard, timeline, metadata,
and production manifest references.

### `scenes` and `scene_versions`

Stores stable scene identity and immutable scene revisions, dependencies,
timing, generation instructions, and output assets.

## Workflow Tables

### `workflow_runs`

Stores workflow definition version, current state, timestamps, pause/cancel
status, budget, and terminal result.

### `jobs`

Stores activity type, state, input schema version, idempotency key, deadline,
attempt limit, provider policy, and artifact references.

### `job_attempts`

Stores each attempt's worker, provider, timing, result, usage, failure class,
and diagnostic reference.

### `pipeline_events`

Append-only owner-visible and system events. Each event includes episode, run,
job, event type, severity, timestamp, and safe display payload.

### `outbox`

Stores tasks that must be dispatched after a committed state transition.

## Knowledge Tables

### `knowledge_sources`

Stable source identity, canonical URL, publisher, domain, trust tier, license,
topic, language, refresh policy, and lifecycle state.

### `source_snapshots`

Immutable fetched version with retrieval time, content hash, MIME type, parser
version, original object, normalized object, and effective dates.

### `knowledge_chunks`

Normalized searchable text with source location, topic tags, age relevance,
full-text search vector, and embedding status.

### `embeddings`

Model ID, model revision, vector dimension, vector value, and source content
hash. Changing the embedding model creates new records.

### `citations`

Links an episode claim or script range to exact source snapshot and chunk.

## Asset Tables

### `assets`

Stable identity and classification such as character, rig, expression,
background, prop, voice, music, SFX, template, scene, or final render.

### `asset_versions`

Immutable object key, hash, media metadata, provenance, generation parameters,
quality state, model revision, and license.

### `asset_usages`

Links an exact asset version to an episode, scene, source, or derivative asset.

### `licenses`

License type, rights holder, evidence reference, commercial permission,
derivative permission, attribution text, territory, effective dates, and review
state.

## Governance Tables

### `policy_versions`

Immutable educational, safety, source, licensing, generation, and publication
rules. Active episodes keep their original policy version.

### `qa_results` and `qa_findings`

Validator version, rule ID, severity, evidence, artifact reference, result, and
repair recommendation.

### `approvals`

Owner identity, episode version, final asset version, file hash, QA report,
timestamp, note, and revocation state.

### `audit_events`

Append-only security and business actions, including actor, request ID, command,
target, before/after references, and timestamp.

## Identifier and Value Standards

- UUIDv7 for sortable public identifiers.
- UTC `timestamptz` for all timestamps.
- ISO currency plus integer micro-units for cost.
- Enumerated states constrained in application and database.
- SHA-256 for content identity and deduplication.
- RFC 3339 for API timestamps.
- BCP 47 for language identifiers.
- MIME type plus detected media type for stored objects.

## Object Storage

```text
  sources/{source_id}/{snapshot_id}/original
  sources/{source_id}/{snapshot_id}/normalized

  assets/{asset_type}/{asset_id}/{version_id}/original
  assets/{asset_type}/{asset_id}/{version_id}/preview
  assets/{asset_type}/{asset_id}/{version_id}/metadata.json

  episodes/{episode_id}/{episode_version_id}/script
  episodes/{episode_id}/{episode_version_id}/storyboard
  episodes/{episode_id}/{episode_version_id}/scenes/{scene_id}
  episodes/{episode_id}/{episode_version_id}/audio
  episodes/{episode_id}/{episode_version_id}/captions
  episodes/{episode_id}/{episode_version_id}/renders
  episodes/{episode_id}/{episode_version_id}/manifest.json
```

Object keys are immutable after successful upload. A correction receives a new
version ID.

## Upload Protocol

```text
  Worker requests upload intent
          |
          v
  Database creates pending asset version
          |
          v
  Worker uploads object
          |
          v
  Worker reports hash and media metadata
          |
          v
  Backend verifies object and marks version ready
```

Incomplete pending uploads are reconciled and removed after a safe interval.

## Search Strategy

Use three search modes:

1. Structured filters for status, type, topic, character, rights, and freshness.
2. PostgreSQL full-text search for precise terms.
3. `pgvector` exact similarity search for semantic retrieval.

At initial scale, exact vector search is simpler and provides perfect recall.
Add HNSW only after query measurements justify approximate search.

Hybrid results combine structured eligibility, text relevance, semantic
relevance, trust tier, and freshness. A semantically similar but blocked source
must never become eligible.

## Index Baseline

- Unique canonical source URL where appropriate
- Unique content hash per source snapshot
- Unique job idempotency key
- B-tree indexes for states, schedules, and foreign keys
- GIN index for full-text search
- B-tree indexes for asset type, license state, and freshness
- Partial indexes for active jobs and pending outbox records
- Vector index deferred until measured need

## Migration Standards

- Alembic owns schema migrations.
- Migrations are reviewed like application code.
- CI upgrades an empty database and a previous-version fixture.
- Production migration is explicit and separate from application startup.
- Use expand-and-contract changes for deployed schema compatibility.
- Large index changes use non-blocking production procedures where supported.
- Destructive changes require backup verification and a rollback plan.

## Backup and Recovery

- Enable managed point-in-time database recovery.
- Enable object versioning where available.
- Export essential metadata nightly.
- Test restoration monthly during early production.
- Record recovery point and recovery time from each exercise.
- Keep infrastructure and schema reproducible from version control.

## Retention

| Record | Initial retention |
| --- | --- |
| Approval and publication audit | Indefinite |
| Cited source snapshots | Indefinite |
| Approved reusable assets | Until archived by owner |
| Final renders and manifests | Indefinite |
| Workflow and job history | One year |
| Detailed raw logs | 90 days |
| Failed temporary media | 30 days |
| Unused generated candidates | 30 days |

Retention changes must not delete artifacts referenced by approved episodes,
citations, licenses, or audits.
