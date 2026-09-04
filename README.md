# Cartoon Studio

Production architecture for an autonomous illustrated 2D children's cartoon
studio.

## Status

Architecture baseline: signed off for implementation on 2026-09-03.

GitHub repository: `https://github.com/Nagasai125/cartoon-studio-`

Expected GitHub Pages URL after the first pushed `main` deployment:
`https://nagasai125.github.io/cartoon-studio-/`

The first runnable foundation is implemented. It includes a production-quality
dashboard shell, typed FastAPI contract, simulated pipeline progression,
database foundation, local infrastructure, tests, and GitHub Pages CI/CD.

## Current Build

```text
  React dashboard -> FastAPI demo control plane -> simulated workflow
          |                    |
          |                    +-> PostgreSQL schema and migrations
          |
          +-> static demo mode for GitHub Pages before API deployment
```

The simulation proves the control-plane contract without spending money or
requiring AI credentials. Provider generation, authentication, durable task
delivery, and publishing remain disabled until their infrastructure is ready.

## Run Locally

Requirements already verified on the development machine:

- Node.js 24 and npm
- Python 3.12 and `uv`
- Docker and Docker Compose

Install dependencies and start local services:

```bash
make setup
make infra-up
make migrate
```

Run these commands in separate terminals:

```bash
make dev-api
make dev-dashboard
```

Open `http://localhost:5173`. The API documentation is available at
`http://localhost:8000/docs`.

Run all checks:

```bash
make check
```

If `VITE_API_BASE_URL` is unset during a production build, the static dashboard
uses clearly labeled demo data. Set the GitHub repository variable
`VITE_API_BASE_URL` after the production API is deployed.

## Product Intent

Cartoon Studio will autonomously create three English episodes per week for
children ages 2-5. Episodes may combine stories, songs, routines, and early
learning activities using recurring illustrated 2D characters.

The system will:

1. Select an under-covered learning objective.
2. Retrieve facts from an approved, versioned knowledge base.
3. Write an original episode and interaction plan.
4. Produce a storyboard, reusable assets, audio, scenes, and a final render.
5. Validate educational, safety, visual, audio, licensing, and technical rules.
6. Repair failed scenes within fixed retry and cost limits.
7. Stop for final owner approval.
8. Publish only the exact approved video.

The system is autonomous production with a human release gate. It is not an
unrestricted agent swarm and cannot publish without owner approval.

## Owner Experience

The dashboard has five primary areas:

| Area | Purpose |
| --- | --- |
| Overview | Weekly schedule, active work, alerts, cost, and storage |
| Productions | Every episode and its current production stage |
| Review | Final videos waiting for approval |
| Library | Live knowledge sources, characters, assets, audio, and licenses |
| Settings | Budgets, schedules, providers, policies, and channel settings |

Normal operation requires only three owner actions:

- Approve a completed episode.
- Reject an episode or selected scenes with feedback.
- Pause production when necessary.

Prompts, seeds, provider payloads, retries, and stack traces remain available in
an Advanced panel but are not part of the primary interface.

## Signed Architecture

```text
  PUBLIC STATIC SHELL                    PRIVATE CONTROL PLANE

  +----------------------+               +----------------------+
  | GitHub Pages         |    HTTPS      | FastAPI API          |
  | React + TypeScript   |-------------->| Cloud Run            |
  | Vite dashboard       |               +----------+-----------+
  +----------+-----------+                          |
             |                                      |
             | OAuth                                v
             v                           +----------------------+
  +----------------------+               | PostgreSQL          |
  | Supabase Auth        |               | Workflow source of  |
  | GitHub owner login   |               | truth + pgvector     |
  +----------------------+               +----------+-----------+
                                                   |
                                       transaction | + outbox
                                                   v
                                        +----------------------+
                                        | Cloud Tasks          |
                                        +----------+-----------+
                                                   |
                                                   v
                                        +----------------------+
                                        | Production Worker    |
                                        | Cloud Run            |
                                        +---+---------+--------+
                                            |         |
                                +-----------+         +-----------+
                                v                                 v
                     +----------------------+          +----------------------+
                     | AI Provider APIs     |          | Private Storage      |
                     | LLM/image/video/TTS  |          | Sources and media    |
                     +----------------------+          +----------------------+

                                       approved hash only
                                                 |
                                                 v
                                       +----------------------+
                                       | YouTube Publisher    |
                                       +----------------------+
```

## Technology Baseline

| Layer | Selection |
| --- | --- |
| Frontend | React, TypeScript, Vite |
| Frontend data | TanStack Query and generated OpenAPI client |
| Styling | Tailwind CSS and accessible UI primitives |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | Managed PostgreSQL with pgvector |
| Authentication | GitHub OAuth, restricted to the owner's immutable ID |
| Storage | Private object storage with expiring signed URLs |
| Orchestration | Coded event-driven state machine |
| Job delivery | Managed HTTP task queue |
| Rendering | Deterministic HTML/SVG 2D renderer and FFmpeg |
| Initial AI execution | Replaceable external provider APIs |
| Backend deployment | Managed containers that can scale to zero |
| Frontend deployment | GitHub Pages through GitHub Actions |
| CI/CD identity | GitHub Actions OpenID Connect, without static cloud keys |

## Architecture Principles

- Keep the owner interface simple even when production is complex.
- Use one modular monolith before considering microservices.
- Keep PostgreSQL authoritative; queues only deliver work.
- Store media in object storage, never in the database or task payloads.
- Version sources, prompts, assets, episodes, policies, and models.
- Make every job idempotent and every external call time-bounded.
- Record provenance and licensing before an asset can be reused.
- Treat retrieved internet content as untrusted data.
- Use deterministic rendering for letters, numbers, captions, and reusable 2D
  characters.
- Put every provider behind an adapter.
- Bound retries and cost; never create an infinite agent loop.
- Bind approval to the final file hash and independently enforce it at publish.

## Documentation Map

| Document | Description |
| --- | --- |
| [DESIGN.md](DESIGN.md) | Complete product and production design |
| [System architecture](docs/architecture/system-architecture.md) | Components, boundaries, APIs, and runtime flow |
| [Workflow architecture](docs/architecture/workflow-architecture.md) | State machine, jobs, retries, budgets, approval |
| [Data architecture](docs/architecture/data-architecture.md) | Schema, versions, knowledge, assets, and retention |
| [Dashboard design](docs/architecture/dashboard-design.md) | Information architecture and UI standards |
| [Knowledge and assets](docs/architecture/knowledge-asset-library.md) | Live library ingestion, search, provenance, and lifecycle |
| [Deployment architecture](docs/architecture/deployment-architecture.md) | Local, staging, production, scaling, and recovery |
| [Security architecture](docs/architecture/security-architecture.md) | Trust boundaries, identity, secrets, and threat controls |
| [CI/CD](docs/architecture/ci-cd.md) | GitHub rules, Actions, Pages, releases, and migrations |

## Repository Target

```text
cartoon-studio/
|-- apps/
|   `-- dashboard/
|-- services/
|   |-- api/
|   `-- worker/
|-- packages/
|   `-- pipeline/
|       |-- domain/
|       |-- workflows/
|       |-- providers/
|       |-- knowledge/
|       |-- media/
|       |-- validation/
|       `-- publishing/
|-- migrations/
|-- infra/
|   |-- github/
|   |-- gcp/
|   `-- supabase/
|-- tests/
|   |-- integration/
|   |-- workflow/
|   `-- e2e/
|-- docs/
|   |-- architecture/
|   |-- operations/
|   |-- product/
|   `-- adr/
|-- .github/
|   `-- workflows/
|-- DESIGN.md
|-- README.md
`-- docker-compose.yml
```

## Delivery Sequence

1. Repository, architecture decisions, local environment, CI, and auth.
2. Dashboard with a simulated end-to-end episode run.
3. Live knowledge and asset library.
4. Durable state machine, task delivery, and provider adapters.
5. Deterministic 2D media and audio production.
6. Automated quality checks and selective regeneration.
7. Hash-bound approval and isolated YouTube publishing.
8. Staging, production, observability, backup, and recovery hardening.

## Explicitly Deferred

- Self-hosted video models
- Multiple users and role-based permissions
- Multiple languages and channels
- Kubernetes
- Separate service per agent
- Dedicated vector database
- n8n as the workflow owner
- Personalized child accounts or child data collection
- Publication without final owner approval

## Sign-Off Conditions

The architecture remains approved while these conditions hold:

- GitHub Pages contains no secrets or private data.
- All commands are authorized by the backend.
- PostgreSQL remains the workflow source of truth.
- Knowledge and assets carry provenance and rights metadata.
- Paid and generative operations have retry and budget limits.
- Generation workers cannot access publishing credentials.
- Publication verifies an approval for the exact final video hash.
