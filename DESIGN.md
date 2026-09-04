# Cartoon Studio Production Design

## 1. Document Purpose

This document defines the production baseline for Cartoon Studio. It describes
what the system must do, how it is divided, how it is operated, and which rules
cannot be bypassed.

Detailed technical decisions are maintained in `docs/architecture` and should
remain consistent with this document.

## 2. Product Definition

Cartoon Studio is an autonomous production system for original, illustrated 2D
educational cartoons for children ages 2-5.

Initial production constraints:

| Constraint | Decision |
| --- | --- |
| Language | English |
| Frequency | Three episodes per week |
| Duration | Two to four minutes |
| Format | Mixed stories, songs, routines, and early learning |
| Visual identity | Illustrated 2D with reusable characters and environments |
| Operator | One owner |
| Human intervention | Final approval only during normal operation |
| Frontend hosting | GitHub Pages static application |
| Generation strategy | APIs first, self-hosted models later |

## 3. Product Goals

- Produce coherent and materially distinct educational episodes.
- Maintain recognizable characters across episodes.
- Make knowledge, sources, assets, costs, and pipeline activity visible.
- Keep ordinary operation understandable without engineering knowledge.
- Permit scene-level repair without regenerating an entire episode.
- Preserve enough data to reproduce and audit every production decision.
- Replace AI providers without redesigning the production system.
- Prevent accidental, unapproved, or modified content from being published.

## 4. Non-Goals

- Imitating another studio's characters, music, visual identity, or scripts.
- Optimizing solely for upload volume or engagement.
- Allowing agents to alter safety, source, licensing, or publishing policies.
- Sending arbitrary web content directly into generation prompts.
- Generating exact educational text inside an image or video model.
- Collecting personal information from children.
- Building true child personalization in the initial YouTube product.

## 5. Quality Definition

An episode is production-ready only when it is:

- Educationally explicit and accurate.
- Supported by approved sources where factual claims are made.
- Age-appropriate in language, pacing, emotion, and action.
- Narratively coherent with a beginning, progression, and resolution.
- Visually consistent with the approved character and environment library.
- Technically correct in audio, captions, timing, and encoding.
- Free from unlicensed or untraceable source material.
- Materially different from previous episodes.
- Approved by the owner in its final rendered form.

## 6. Product Surface

```text
  +---------------------------------------------------------------+
  | Cartoon Studio                                                |
  +----------------+----------------------------------------------+
  | Overview       | This week: 3 planned, 1 active, 1 review    |
  | Productions    |                                              |
  | Review         | Active episode                               |
  | Library        | [Planning] -> [Scenes 8/12] -> [Rendering]   |
  | Settings       |                                              |
  |                | Alerts                  Monthly cost          |
  |                | 1 scene retrying        $42.18 / $200        |
  +----------------+----------------------------------------------+
```

The dashboard presents productions and assets, not infrastructure internals.
Engineering detail is available through an Advanced view.

## 7. Logical Architecture

```text
                    +-------------------------+
                    | Owner Dashboard         |
                    | observe, review, control|
                    +------------+------------+
                                 |
                                 v
                    +-------------------------+
                    | Control API             |
                    | auth and domain rules   |
                    +------------+------------+
                                 |
              +------------------+------------------+
              |                  |                  |
              v                  v                  v
     +----------------+ +----------------+ +----------------+
     | Production     | | Knowledge and  | | Approval and   |
     | state machine  | | asset library  | | publishing     |
     +--------+-------+ +--------+-------+ +--------+-------+
              |                  |                  |
              +------------------+------------------+
                                 |
                                 v
                    +-------------------------+
                    | PostgreSQL             |
                    | authoritative metadata |
                    +------------+------------+
                                 |
                                 v
                    +-------------------------+
                    | Async task delivery     |
                    +------------+------------+
                                 |
                                 v
                    +-------------------------+
                    | Production worker       |
                    +------------+------------+
                                 |
       +-------------------------+-------------------------+
       |                         |                         |
       v                         v                         v
  +------------+          +-------------+          +-------------+
  | AI APIs    |          | Renderer    |          | Storage     |
  +------------+          +-------------+          +-------------+
```

## 8. Domain Modules

### Curriculum

Owns learning objectives, developmental level, coverage, prerequisites, and
content diversity rules.

### Knowledge

Owns trusted sources, snapshots, extracted claims, chunks, embeddings,
citations, freshness, and source trust tiers.

### Creative Direction

Owns series rules, characters, environments, visual grammar, episode formats,
story constraints, interactive moments, and prompt templates.

### Production

Owns episode versions, scenes, provider requests, audio, deterministic 2D
composition, rendering, and generated manifests.

### Validation

Owns factual, educational, narrative, visual, audio, accessibility, licensing,
technical, and similarity checks.

### Workflow

Owns states, transitions, jobs, retries, budgets, events, pause/cancel behavior,
and recovery.

### Approval

Owns the final review record, approved video hash, reviewer identity, timestamp,
and invalidation rules.

### Publishing

Owns private upload, scheduling, YouTube metadata, made-for-kids designation,
publication status, and upload recovery.

## 9. Episode Contract

Each episode starts as a typed specification containing at least:

```json
{
  "series_id": "uuid",
  "learning_objective_id": "uuid",
  "age_band": "3-5",
  "format": "story_with_song",
  "target_duration_seconds": 180,
  "characters": ["uuid"],
  "source_snapshot_ids": ["uuid"],
  "interaction_requirements": {
    "minimum_questions": 2,
    "minimum_response_pause_seconds": 3
  },
  "production_budget_micros": 15000000,
  "policy_version_id": "uuid"
}
```

Generated stages add immutable versions rather than modifying approved output.

## 10. Production Flow

```text
  Weekly schedule
        |
        v
  Select objective and format
        |
        v
  Retrieve source snapshots and citations
        |
        v
  Generate brief and script
        |
        v
  Validate facts, pedagogy, age, and originality
        |
        v
  Create storyboard and asset plan
        |
        v
  Reuse approved assets and generate missing assets
        |
        v
  Produce scenes and audio in parallel
        |
        v
  Validate and selectively repair scenes
        |
        v
  Render video, captions, music, and manifest
        |
        v
  Run final automated validation
        |
        v
  OWNER REVIEW
     |       |
 approve   reject
     |       |
     v       v
 publish   repair selected work
```

## 11. Autonomy Boundaries

Agents are named production roles implemented as typed functions or workflows:

- Curriculum Planner
- Researcher
- Writer
- Episode Director
- Art Director
- Audio Producer
- Animation Producer
- Quality Reviewer
- Publisher

They do not freely converse. The state machine supplies structured input and
validates structured output.

Agents cannot:

- Modify policy versions.
- Add arbitrary domains to the source allowlist.
- Approve licensing exceptions.
- Raise their own budgets.
- Disable validators.
- Approve an episode.
- Access publishing credentials.
- Publish content.

## 12. Illustrated 2D Production Strategy

Reusable, deterministic assets are the default:

- Character rigs and proportions
- Expressions and mouth shapes
- Pose and gesture library
- Environments and reusable scene layouts
- Props and educational objects
- Text, letters, numbers, shapes, and captions
- Camera moves and transitions
- Music stems and sound effects

Generative models provide controlled additions:

- New background concepts
- Prop variants
- Expression candidates
- Imagination sequences
- Selective image-to-video moments

Educational text and counts are rendered deterministically. Generative video is
not trusted to spell words or preserve exact quantities.

## 13. Live Knowledge and Asset Library

The Library answers four questions:

1. What does the system know?
2. Where did that knowledge come from?
3. What production assets do we own and have permission to use?
4. Where has each source or asset been used?

The owner can search and filter by topic, trust, status, freshness, license,
character, format, episode usage, and generation model.

The knowledge system uses PostgreSQL full-text search plus `pgvector`. A second
vector database is not justified at initial scale.

## 14. Provider Strategy

All providers implement internal interfaces such as:

```text
LanguageProvider.plan_episode()
LanguageProvider.write_script()
ImageProvider.generate_asset()
VideoProvider.generate_scene()
SpeechProvider.synthesize_dialogue()
EmbeddingProvider.embed_documents()
```

Provider-specific request and response formats never escape the adapter layer.
The application records the provider, model, model revision, normalized usage,
cost, request hash, response hash, and timing.

The first release uses APIs to validate the product. Open-weight GPU workers can
later implement the same interfaces.

## 15. Approval Invariant

```text
  final.mp4
      |
      v
  SHA-256 hash ----------------------+
      |                              |
      v                              v
  Owner review                 Approval record
                                     |
                                     v
                            Publisher recomputes hash
                                     |
                          +----------+----------+
                          |                     |
                        match                mismatch
                          |                     |
                          v                     v
                       publish                 block
```

An approval becomes invalid when:

- The final video changes.
- The episode version changes.
- The final QA report is superseded.
- The approval is explicitly revoked.

## 16. Environments

### Local

Docker Compose provides PostgreSQL with `pgvector`, object storage, and fake
provider endpoints. The dashboard, API, and worker run locally with hot reload.

### Staging

Staging uses separate managed data, storage, OAuth, provider keys, callbacks,
and YouTube test configuration. It never shares production credentials.

### Production

Production uses protected deployment identity, private worker endpoints,
managed backups, alerting, and real publishing credentials.

## 17. CI/CD Standards

- Short-lived branches and pull requests.
- Required lint, type, test, build, and migration checks.
- No paid AI calls in pull-request CI.
- GitHub Actions pinned to immutable commit SHAs.
- Minimum token permissions per job.
- OIDC temporary credentials for cloud deployment.
- Container scan, SBOM, and signature before deployment.
- Deploy images by immutable digest.
- Apply migrations explicitly, never during application startup.
- Deploy the Pages frontend automatically after a successful `main` build.
- Require a protected environment action for production backend changes.

## 18. Security Standards

- GitHub Pages is a public shell and contains no private information.
- Backend authorization is required for every business operation.
- The owner is allowlisted by immutable GitHub account ID.
- Buckets are private; previews use short-lived signed URLs.
- Retrieval content is isolated as untrusted data.
- Source fetching blocks private IP ranges and unsafe redirects.
- Webhooks require signatures, timestamps, and replay protection.
- Provider and YouTube secrets remain in managed secret storage.
- Publishing credentials are unavailable to generation workers.
- Logs exclude tokens and unnecessary raw content.
- The product collects no child personal information.

## 19. Reliability and Operations

Initial service objectives:

| Concern | Target |
| --- | --- |
| Dashboard and API availability | 99.5 percent monthly |
| Visible pipeline event delay | Under 10 seconds |
| Duplicate publishing | Zero tolerated |
| Lost completed jobs | Zero tolerated |
| Approval bypass | Zero tolerated |
| Recovery | Managed database point-in-time recovery |

Important metrics include queue age, job duration, retry count, provider failure
rate, cost per stage, cost per episode, validation failures, storage growth,
source freshness, approval turnaround, and publication failures.

## 20. Delivery Phases

### Phase 1: Foundation

Create the monorepo, architecture decisions, local environment, CI, database,
API shell, frontend shell, and owner authentication.

### Phase 2: Simulated Control Plane

Build the dashboard and run a complete fake episode through every state. Prove
pause, retry, rejection, approval, and live event behavior before integrating
paid providers.

### Phase 3: Knowledge and Assets

Implement ingestion, snapshots, citations, full-text and semantic search,
private storage, asset versions, licenses, and usage tracking.

### Phase 4: Production Workflow

Implement the state machine, outbox, task dispatcher, provider adapters, budget
controls, and scene-level parallelism.

### Phase 5: Media

Implement the reusable 2D asset system, voice, audio, timeline composition,
captions, FFmpeg rendering, and production manifest.

### Phase 6: Validation and Publishing

Implement automated quality gates, selected-scene repair, hash-bound approval,
private YouTube upload, scheduling, and publication audit.

### Phase 7: Hardening

Complete staging and production deployment, observability, alerts, backup,
restore exercises, incident response, and cost reporting.

## 21. Acceptance Criteria

The first production milestone is complete when:

- The owner can authenticate and access no data before authentication.
- A scheduled episode can run without manual intervention.
- Every factual claim shown in review has a source snapshot.
- Every reused asset has a valid rights record.
- Failed scenes can be regenerated independently.
- Costs and retries are visible while the episode runs.
- The final video, captions, sources, and QA report appear in Review.
- Publishing an unapproved or modified video is impossible.
- The system can recover from API and worker restarts.
- A three-episode weekly schedule can execute within its configured budget.

## 22. Architecture Sign-Off

Decision: approved for implementation.

The approved baseline is a private monorepo containing a React/Vite static
dashboard, FastAPI modular monolith, coded PostgreSQL-backed state machine,
managed asynchronous task delivery, PostgreSQL plus `pgvector`, private object
storage, provider adapters, deterministic 2D rendering, and isolated publishing
with hash-bound final approval.

Changes to the approval invariant, system of record, public/private boundary,
or publishing isolation require a new architecture decision record.
