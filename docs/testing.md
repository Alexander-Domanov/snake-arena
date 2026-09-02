# Testing Strategy

Interview Canvas is tested at four layers. Each layer answers a different
question and runs in a different environment; together they make sure that a
green pipeline means the app actually works, not just that it imports.

| Layer | What it verifies | Environment | Runs in CI |
|-------|------------------|-------------|------------|
| Backend unit tests | models, pydantic schemas, DB helpers | in-memory SQLite | `backend-unit` job |
| API integration tests | the 4 endpoints over the real FastAPI app | in-memory SQLite (dependency override) | `backend-unit` job |
| Frontend tests | contract behavior of `app.js` (payloads, reloads, error handling) | jsdom + node:test | `frontend` job |
| Integration tests (Postgres) | real database: migrations, CRUD, `/healthz` | real Postgres 16 | `integration` job |
| E2E tests | two-session board flow through the real container | docker-compose stack + Playwright (Chromium) | `e2e` job |
| Image build | the Dockerfile builds and compose config is valid | Docker | `build` job |

## Running locally

```bash
# Backend unit + API integration tests (in-memory SQLite, no services needed)
uv run pytest

# Integration tests against real Postgres (docker compose up -d db first,
# or use the CI-style env vars)
uv run pytest tests/integration

# E2E tests against the full compose stack (builds the container, needs Docker)
docker compose up -d --build
uv run pytest e2e

# Frontend tests (jsdom + node:test)
npm install    # once
npm test
```

## Test inventory

- `tests/test_models.py` — SQLAlchemy models: fields, defaults, cascade delete
  on board deletion, UUID serialization.
- `tests/test_database.py` — `DATABASE_URL` handling and SQLite session setup.
- `tests/test_api.py` — API contract: 201/204/200/404/422, enum validation
  (`sticky_note` vs `sticky`), UUID validation, cascade delete, date format,
  board lifecycle (create → get → add elements → delete).
- `tests/frontend/app.test.mjs` — the real `frontend/index.html` + `app.js`
  loaded into jsdom with a mocked `fetch` (an in-memory fake mirroring
  `openapi.yaml`): create a board on load, add/delete elements with correct
  payloads, reload after mutations, `?board=<id>` join flow, error handling.
- `tests/integration/` — real Postgres: Alembic migrations apply cleanly
  (`test_migrations.py`), CRUD persists and survives reconnects
  (`test_crud_postgres.py`), `/healthz` reports database health
  (`test_healthz.py`).
- `e2e/test_two_sessions.py` — Playwright scenario: two browser sessions on the
  same board; an element added by the candidate becomes visible to the
  interviewer after reload (server as source of truth).

## Isolation rules

- Unit tests never touch a real database (in-memory SQLite, fresh per test).
- Integration tests create a dedicated `canvas_test` database and drop it after
  the session — the dev/CI `canvas` database is never modified.
- E2E tears the compose stack down with `docker compose down -v` (fresh volume
  on the next run, no state leaks between runs).
- CI needs no secrets: `ci.yml` runs on every pull request and uses only
  ephemeral Postgres service containers.

## Contract-first note

`openapi.yaml` is the source of truth. The enum test for element types exists
because the frontend historically sent `sticky` instead of `sticky_note` —
a spec does not protect against typos, tests do.
