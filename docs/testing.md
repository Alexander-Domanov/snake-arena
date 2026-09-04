# Testing Strategy

Interview Canvas is tested at several layers. Each layer answers a different
question and runs in a different environment; together they make sure that a
green pipeline means the app actually works, not just that it imports.

| Layer | What it verifies | Environment | Runs in CI |
|-------|------------------|-------------|------------|
| Lint | ruff (E/F/W/I/UP/B rules) over backend, tests, e2e, alembic, on-call-engineer | uv | `lint` job |
| Backend unit tests | models, pydantic schemas, DB helpers | in-memory SQLite | `backend-unit` job |
| API integration tests | the 6 endpoints over the real FastAPI app | in-memory SQLite (dependency override) | `backend-unit` job |
| Frontend tests | contract behavior of `app.js` (payloads, reloads, PATCH persistence, error handling) | jsdom + node:test | `frontend` job |
| Integration tests (Postgres) | real database: migrations, CRUD + PATCH updates, `/healthz` | real Postgres 16 | `integration` job |
| E2E tests | two-session board flow: shared edits persist across reloads | docker-compose stack + Playwright (Chromium) | `e2e` job |
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
  board lifecycle (create → get → add → PATCH update → delete).
- `tests/test_telemetry.py` — OTel application metrics (in-memory
  MeterProvider, no collector): boards/elements counters, creation-failure
  counter by reason, active-board gauge, resource labels
  (service.name/service.version/deployment.environment), and the env gating
  (telemetry off without `OTEL_EXPORTER_OTLP_ENDPOINT`).
- `tests/frontend/app.test.mjs` — the real `frontend/index.html` + `app.js`
  loaded into jsdom with a mocked `fetch` (an in-memory fake mirroring
  `openapi.yaml`): create a board on load, add/delete elements with correct
  payloads, reload after mutations, `?board=<id>` join flow, PATCH persistence
  (text on blur, position on pointerup, no-PATCH guards), error handling.
- `tests/integration/` — real Postgres: Alembic migrations apply cleanly
  (`test_migrations.py`), CRUD + PATCH updates persist and survive reconnects
  (`test_crud_postgres.py`: text-only, position-only, both fields, clear-null,
  empty-body no-op, 404), `/healthz` reports database health
  (`test_healthz.py`).
- `e2e/test_two_sessions.py` — Playwright scenario: two browser sessions on the
  same board; the candidate adds a sticky note, edits its text and drags it,
  and the interviewer sees the persisted text AND position after a reload
  (server as source of truth), then a delete propagates the same way.

## Isolation rules

- Unit tests never touch a real database (in-memory SQLite, fresh per test)
  and always run — even without Docker/Postgres.
- Integration tests require a reachable Postgres. If it is unavailable they
  are **skipped** (not failed) at collection time — only tests carrying the
  `integration` marker, so a plain `uv run pytest` on a machine without
  Docker still runs the full unit suite and reports integration as skipped.
  (Historical note: the collection hook used to skip *every* test in the
  session when Postgres was down, which silently turned the CI unit job into
  a green no-op; the marker filter fixes that.)
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
