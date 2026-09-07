.PHONY: setup dev-api dev-dashboard dry-run infra-up infra-down migrate check

setup:
	uv sync
	npm ci

dev-api:
	uv run uvicorn cartoon_studio.api.main:app --reload --port 8000

dev-dashboard:
	npm run dev

dry-run:
	PYTHONPATH=packages/pipeline/src uv run python -m cartoon_studio.workflows.run_episode --brief config/episodes/letter-b.json --policy config/workflows/dry-run-v1.json --checkpoint-out .data/workflow/checkpoint.json --dashboard-out apps/dashboard/public/data/dashboard.json --run-id local-dry-run

infra-up:
	docker compose up -d --wait postgres minio

infra-down:
	docker compose down

migrate:
	uv run alembic upgrade head

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run pyright
	uv run pytest
	npm run lint
	npm run typecheck
	npm run test
	npm run build
