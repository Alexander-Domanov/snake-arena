# Interview Canvas

Collaborative whiteboard for system design interviews: sticky notes and basic
shapes on a shared board. This is the Module 2 deliverable — a full-stack app
that runs locally: a static frontend and a FastAPI backend talking over an
OpenAPI contract, with data persisted in SQLite.

## Repository layout

```text
product-spec.md          product requirements (user stories, acceptance criteria, non-goals)
AGENTS.md                project conventions and commands for agents
openapi.yaml             API contract (source of truth)
frontend/                plain HTML/CSS/JS prototype (no build step)
backend/                 FastAPI app (main, routes, services, models, schemas, database)
tests/                   pytest: unit tests for models/schemas + API integration tests
docs/ai-usage-report.md  report on AI usage during development
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — manages the Python environment
  (downloads a managed Python 3.11+ automatically if the system one is older)
- A browser — the frontend is plain HTML/CSS/JS

## Run locally

Start the backend (from the repo root):

```bash
uv run uvicorn backend.main:app --reload
```

- API: http://localhost:8000
- Interactive docs (Swagger UI): http://localhost:8000/docs
- Machine-readable contract: http://localhost:8000/openapi.json

The SQLite file `db.sqlite3` is created in the repo root on first start
(it is gitignored).

Open the frontend — either directly from disk or via a tiny static server:

```bash
# Option A: double-click / open frontend/index.html in a browser
open frontend/index.html

# Option B: static server
python3 -m http.server 8123 -d frontend   # then open http://localhost:8123
```

On page load the frontend creates a new board (`POST /boards`) and renders its
elements; elements are added/deleted through the API and the board is reloaded
after every mutation.

## Tests

```bash
uv run pytest
```

Runs 30 tests: unit tests for SQLAlchemy models and pydantic schemas
(`tests/test_models.py`) and integration tests for all API endpoints
(`tests/test_api.py`, isolated in-memory database).

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./db.sqlite3` | SQLAlchemy connection string. Set to a Postgres URL to swap databases without code changes (install the matching driver, e.g. `psycopg`) |

## API contract

`openapi.yaml` is the source of truth for the API. The backend implements it
exactly; FastAPI's generated `/openapi.json` mirrors the same four endpoints:

- `POST /boards` — create a board
- `GET /boards/{board_id}` — get a board with all elements
- `POST /boards/{board_id}/elements` — add an element (sticky_note / rectangle / circle)
- `DELETE /elements/{element_id}` — delete an element
