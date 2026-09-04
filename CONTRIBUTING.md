# Contributing

## Local Setup

Requirements:

- Node.js 24 or later
- Python 3.12
- `uv`
- Docker with Docker Compose

Install dependencies:

```bash
make setup
```

Start PostgreSQL and object storage:

```bash
make infra-up
make migrate
```

Run the API and dashboard in separate terminals:

```bash
make dev-api
make dev-dashboard
```

The dashboard is available at `http://localhost:5173` and the API at
`http://localhost:8000`.

## Quality Checks

Run all local checks before opening a pull request:

```bash
make check
```

## Development Rules

- Use a short-lived branch.
- Keep domain rules out of HTTP handlers and provider adapters.
- Add tests for state transitions and production invariants.
- Do not add secrets to source files or `VITE_*` variables.
- Do not add paid provider calls to ordinary tests.
- Create a migration for every schema change.
- Update architecture documentation when a signed decision changes.
