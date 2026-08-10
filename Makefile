.PHONY: install backend-install frontend-install backend-dev frontend-dev test lint typecheck

backend-install:
	cd backend && uv sync

frontend-install:
	cd frontend && npm install

install: backend-install frontend-install

backend-dev:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

frontend-dev:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest
	cd frontend && npm test

lint:
	cd backend && uv run ruff check .
	cd frontend && npm run lint

typecheck:
	cd backend && uv run mypy app
	cd frontend && npm run typecheck
