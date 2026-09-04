---
name: contract-first-feature
description: Implement an API feature in Interview Canvas end-to-end — openapi.yaml first, then backend, tests, frontend, checks, commit.
---

# Contract-first feature implementation

Use this skill whenever a task asks you to implement (or extend) an API
feature in this repository. The contract in `openapi.yaml` is the source of
truth (AGENTS.md rule); the backend must implement exactly what the contract
declares, and tests must prove it at every layer.

Read `product-spec.md` and `openapi.yaml` first. If the requested feature
contradicts the spec or a listed non-goal, stop and say so instead of
improvising.

## Procedure

1. **Contract first.** Edit `openapi.yaml`:
   - add/change the `paths` entry, request/response schemas and reusable
     `components` (path parameters, 404/422 responses);
   - include request/response examples; keep them valid against the schemas;
   - status codes follow repo conventions: create → `201`, delete → `204`,
     read/update → `200`, missing resource → `404`, invalid payload → `422`.
2. **Backend mirrors the contract.**
   - `backend/schemas.py` — pydantic request/response models exactly matching
     the OpenAPI schemas (field names, types, `max_length` bounds);
   - `backend/services.py` — all DB logic, routes stay thin; raise
     `HTTPException(404, ...)` for missing resources;
   - `backend/routes.py` — one thin route per path; keep the existing idioms:
     `uuid.UUID` path annotations (garbage id → 422), `selectinload` when a
     response serializes a relationship (avoids `DetachedInstanceError`),
     RFC3339 UTC `Z` date serialization via the schema field serializers,
     telemetry counters for user-visible successes/failures (see
     `backend/telemetry.py` and `tests/test_telemetry.py`).
3. **Tests, not just code.**
   - unit/API tests in `tests/test_api.py` against in-memory SQLite
     (dependency override) covering the new status codes: 201/204/200/404/422,
     enum validation, uuid validation, cascade behaviour;
   - integration tests in `tests/integration/` against real Postgres when the
     feature touches persistence or migrations;
   - frontend jsdom tests in `tests/frontend/app.test.mjs` when the UI
     changes (payloads, reload-after-mutation behaviour);
   - telemetry tests in `tests/test_telemetry.py` when a metric is added.
4. **Run the real checks** (not a subset, and confirm nothing was skipped):
   ```bash
   uv run ruff check backend tests e2e alembic on-call-engineer
   uv run pytest -m "not integration" -q          # expect e.g. "N passed"
   npm test                                        # when frontend changed
   # integration against real Postgres, if available:
   docker compose up -d db && uv run pytest tests/integration -q
   ```
   A green line that says "deselected/skipped" for your new tests is NOT
   green — verify your tests actually ran.
5. **Sync docs that enumerate the API** (README "API contract" section,
   `docs/testing.md` inventory, `docs/ai-usage-report.md` stage tables) when
   endpoint lists or test counts change.
6. **Commit** with a conventional message (`feat(scope): ...`) that names the
   endpoint(s) touched. Lint before committing.

## Pitfalls learned in this repo

- Frontend enum values differ from API enums: `sticky` ≠ `sticky_note`,
  `rect` ≠ `rectangle` — map toolbar keys to API types explicitly.
- FastAPI 422 `detail` is an array; stringify the first error message, not
  the whole object, for user-facing banners.
- `exclude_unset` in partial updates distinguishes an omitted field from an
  explicit `null` (used to clear text) — keep that semantic.
- Element positions and sizes: keep `width`/`height` positive (`gt=0`);
  cascade counters reset after reload, so offset new elements deterministically.
- Never hardcode API URLs in the frontend; use same-origin relative paths.
