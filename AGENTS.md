# AGENTS.md

## Commands

- `uv sync` – install dependencies
- `uv run uvicorn backend.main:app --reload` – start FastAPI dev server
- `uv run pytest` – run unit/API tests (integration tests are skipped unless Postgres is up: `docker compose up -d`)
- `uv run pytest tests/test_api.py` – run specific test file
- `uv run pytest -k delete` – run tests matching a keyword
- `uv run pytest tests/integration` – run integration tests against real Postgres (start it with: `docker compose up -d db`)
- `uv run pytest e2e` – run Playwright E2E tests (start the full stack with: `docker compose up -d --build`)
- `uv run ruff check backend tests e2e alembic on-call-engineer` – run the CI linter
- `npm test` – run frontend tests (jsdom + node:test; `npm install` once)
- `docker compose -f observability/docker-compose.yml up -d --build` – start the local observability stack (OTel Collector, Prometheus, Loki, Tempo, Grafana, Alertmanager); see `observability/README.md`
- `docker compose -f observability/docker-compose.yml down -v` – stop the observability stack
- `uv run on-call-engineer/poll.py --once` – dry-run the Alertmanager on-call poller; set `ONCALL_AGENT_CMD` (with `{prompt}`) to delegate real alerts to a headless agent; see `on-call-engineer/README.md`
- `uv run python -m openapi_generator` – generate client (if needed)

## Rules

- Dependencies go in `pyproject.toml`; ask before adding new ones.
- All API changes must be reflected in `openapi.yaml` first.
- Frontend must use OpenAPI-generated client (or manual fetch) – no hardcoded URLs.
- Commit after each meaningful step (spec, frontend, openapi, backend, tests).
- Read `product-spec.md` before implementing any feature.
- Keep SQLAlchemy models in `backend/models.py`, pydantic API schemas in `backend/schemas.py`, routes in `backend/routes.py`, services in `backend/services.py`.
- Tests must cover both unit (models) and integration (API) layers.
- `main` is protected: changes go through a PR, all CI checks must pass, direct pushes are blocked.
- Lint with ruff before committing (`uv run ruff check backend tests e2e alembic on-call-engineer`).

## Documents

- `product-spec.md` – product requirements and user stories
- `openapi.yaml` – API contract (source of truth)
- `docs/testing.md` – test strategy and isolation rules
- `docs/deployment.md` – deployment architecture (Render, environments, secrets)
- `docs/release-process.md` – CI gate, deploy flow, rollback
- `docs/ai-usage-report.md` – report on AI usage
- `db.sqlite3` – SQLite database, created automatically in the repo root at server startup (gitignored)
- `backend/` – FastAPI backend code
- `frontend/` – frontend static files
- `tests/` – pytest tests
- `observability/` – local OTel stack (separate compose project): collector, Prometheus, Loki, Tempo, Grafana, Alertmanager (`observability/README.md`)
- `on-call-engineer/` – Alertmanager poller that hands firing alerts to a headless coding agent (`on-call-engineer/README.md`)
