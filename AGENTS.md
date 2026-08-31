# AGENTS.md

## Commands

- `uv sync` – install dependencies
- `uv run uvicorn backend.main:app --reload` – start FastAPI dev server
- `uv run pytest` – run all tests
- `uv run pytest tests/test_api.py` – run specific test file
- `uv run pytest -k delete` – run tests matching a keyword
- `npm test` – run frontend tests (jsdom + node:test; `npm install` once)
- `uv run python -m openapi_generator` – generate client (if needed)

## Rules

- Dependencies go in `pyproject.toml`; ask before adding new ones.
- All API changes must be reflected in `openapi.yaml` first.
- Frontend must use OpenAPI-generated client (or manual fetch) – no hardcoded URLs.
- Commit after each meaningful step (spec, frontend, openapi, backend, tests).
- Read `product-spec.md` before implementing any feature.
- Keep SQLAlchemy models in `backend/models.py`, pydantic API schemas in `backend/schemas.py`, routes in `backend/routes.py`, services in `backend/services.py`.
- Tests must cover both unit (models) and integration (API) layers.

## Documents

- `product-spec.md` – product requirements and user stories
- `openapi.yaml` – API contract (source of truth)
- `docs/ai-usage-report.md` – report on AI usage
- `db.sqlite3` – SQLite database, created automatically in the repo root at server startup (gitignored)
- `backend/` – FastAPI backend code
- `frontend/` – frontend static files
- `tests/` – pytest tests
