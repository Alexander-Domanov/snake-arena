# Interview Canvas

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-green)
![SQLite](https://img.shields.io/badge/SQLite-3-blue)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-green)
![pytest](https://img.shields.io/badge/tests-48%20passed-brightgreen)
![frontend tests](https://img.shields.io/badge/frontend%20tests-15%20passed-brightgreen)
![Docker](https://img.shields.io/badge/Docker-multi--stage-blue)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-green)](.github/workflows/ci.yml)
[![Deploy](https://img.shields.io/badge/Deploy-Render-blueviolet)](render.yaml)
![License](https://img.shields.io/badge/license-MIT-blue)
[![DataTalks.Club](https://img.shields.io/badge/DataTalks.Club-AI%20Dev%20Tools%20Zoomcamp%202026-purple)](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp)

Collaborative whiteboard for system design interviews: sticky notes and basic
shapes on a shared board. This is the Module 3 deliverable — the Module 2
full-stack app (static frontend + FastAPI backend over an OpenAPI contract,
SQLite for local dev) proven by unit/integration/E2E tests, packaged in a
container, checked by CI on every pull request, and deployed to staging
(development) and production on Render — staging automatically on merge to
`main`, production via manual promotion.

## Repository layout

```text
product-spec.md          product requirements (user stories, acceptance criteria, non-goals)
AGENTS.md                project conventions and commands for agents
openapi.yaml             API contract (source of truth)
frontend/                plain HTML/CSS/JS prototype (no build step)
backend/                 FastAPI app (main, routes, services, models, schemas, database)
alembic/                 DB migrations (applied automatically on startup/deploy)
tests/                   pytest unit/API + integration (real Postgres) + frontend jsdom tests
e2e/                     Playwright E2E tests against the docker-compose stack
Dockerfile               multi-stage image (uv stage + runtime, no Node stage)
docker-compose.yml       local full stack: Postgres + app with healthchecks
.github/workflows/       ci.yml (every PR) and deploy.yml (build → GHCR → staging; manual prod promotion)
render.yaml              Render Blueprint: managed Postgres (provisioning record; web services are image-backed from GHCR)
docs/                    testing/deployment/release-process docs, AI usage report, screenshots
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — manages the Python environment
  (downloads a managed Python 3.11+ automatically if the system one is older)
- A browser — the frontend is plain HTML/CSS/JS
- Node.js 18+ — only needed for the frontend tests

## Live

- Production: https://interview-canvas.onrender.com
- Staging: https://interview-canvas-staging.onrender.com
- Both expose `GET /healthz` → `{"status":"ok","database":"ok"}`

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

## Run with Docker (Postgres, full stack)

The repository ships a container image and a Compose stack that mirrors
production: Postgres 16 + the app, with healthchecks.

```bash
docker compose up -d --build
```

- App: http://localhost:8100 (frontend served by FastAPI)
- API docs: http://localhost:8100/docs
- Postgres is exposed on localhost:5432 (used by the integration tests too)

Build just the image:

```bash
docker build -t interview-canvas:latest .
```

On container start the entrypoint applies DB migrations (`alembic upgrade
head`) before launching the server, exactly like production on Render.

## CI/CD

- **CI** (`.github/workflows/ci.yml`) runs on every pull request: lint (ruff),
  backend unit tests, frontend jsdom tests, integration tests against a real
  Postgres service container, E2E tests against the docker-compose stack
  (Playwright), and a Docker image build.
- **Deploy** (`.github/workflows/deploy.yml`) runs on push to `main`: it
  builds the image and pushes it to GHCR (`ghcr.io/alexander-domanov/snake-arena`,
  tagged `YYYYMMDD-HHMMSS-<sha>`), then deploys that exact tag to **staging**
  (development) via a Render deploy hook, waiting for `/healthz`. Production
  is **not** automatic: promote manually via
  **Actions → Deploy → Run workflow → `production`**, pasting the image tag
  verified on staging (a guard requires staging to be healthy first). Rollback
  is done in the Render dashboard (previous successful deploy).

Deployment details, the release process and the test strategy are documented
in `docs/deployment.md`, `docs/release-process.md` and `docs/testing.md`.

## Screenshots

The board — sticky notes and shapes created through the real API:

![Board](docs/screenshots/board.png)

Interactive API docs generated by FastAPI at `/docs`:

![API docs](docs/screenshots/api-docs.png)

## Tests

The full strategy is described in `docs/testing.md`. Quick start:

Backend unit + API tests (in-memory SQLite, no services):

```bash
uv run pytest -m "not integration and not e2e"
```

Integration tests against real Postgres (start `docker compose up -d db` first,
or run the whole compose stack):

```bash
docker compose up -d --build
uv run pytest tests/integration
```

E2E (Playwright, against the docker-compose stack):

```bash
uv run pytest e2e
```

Frontend (contract behavior of `app.js` in jsdom):

```bash
npm install   # once
npm test
```

CI runs all of these on every pull request (`.github/workflows/ci.yml`).

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./db.sqlite3` | SQLAlchemy connection string. Set to a Postgres URL to swap databases without code changes (install the matching driver, e.g. `psycopg`) |

## How it was built (AI-native full-stack workflow)

This project follows the AI-native development workflow from the
[AI Dev Tools Zoomcamp 2026](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp):

Modules 1–2 (spec → frontend → contract → backend → integration):

1. **Spec first** – `product-spec.md` defines user stories, acceptance criteria,
   and non-goals before any code.
2. **Frontend prototype** – a plain HTML/CSS/JS prototype with mocked state was
   built to validate UX.
3. **OpenAPI contract** – `openapi.yaml` was created as the single source of truth
   between frontend and backend.
4. **Backend implementation** – FastAPI + SQLAlchemy were implemented strictly
   against the contract, with SQLite persistence and a database-agnostic design
   (`DATABASE_URL`).
5. **Testing** – unit and integration tests (pytest) cover the backend; frontend
   logic is tested with jsdom + node:test.
6. **Integration** – the frontend was switched from mocks to real API calls, with
   CORS and error handling.

Module 3 (test, containerize, deploy):

7. **Real-stack tests** – Alembic migrations, `/healthz`, and CRUD against a real
   Postgres (`tests/integration/`), plus a Playwright E2E scenario running the
   whole docker-compose stack (`e2e/`).
8. **Containerization** – multi-stage `Dockerfile` (uv, no Node stage) and
   `docker-compose.yml` (Postgres + app, healthchecks); migrations run in the
   container entrypoint.
9. **CI** – `.github/workflows/ci.yml` runs lint (ruff), unit, frontend,
   integration, E2E and the image build on every pull request (no secrets
   needed); branch protection on `main` requires every check to pass.
10. **Deploy + CD** – the image is built once in CI and pushed to GHCR with a
    `YYYYMMDD-HHMMSS-<sha>` tag; Render services are image-backed and pull that
    exact image. `.github/workflows/deploy.yml` deploys staging automatically
    on push to `main`; production is promoted manually (Module 4 dev/prod
    model) with the same image tag. Docs: `docs/testing.md`,
    `docs/deployment.md`, `docs/release-process.md`.
11. **Context engineering** – `AGENTS.md` provides commands and rules for AI coding
    agents.
12. **AI usage report** – `docs/ai-usage-report.md` documents prompts, bugs,
    lessons, and the split between AI and human contributions.

All steps were verified by running the app locally and passing the CI suites
(unit, integration against Postgres, E2E on the compose stack).

📚 Course materials and module requirements: [Module 3 README](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/03-deployment/README.md)

## API contract

`openapi.yaml` is the source of truth for the API. The backend implements it
exactly; FastAPI's generated `/openapi.json` mirrors the same five endpoints:

- `POST /boards` — create a board
- `GET /boards/{board_id}` — get a board with all elements
- `POST /boards/{board_id}/elements` — add an element (sticky_note / rectangle / circle)
- `PATCH /elements/{element_id}` — partially update an element (x, y, text) — persists drag-and-drop position and sticky note text edits
- `DELETE /elements/{element_id}` — delete an element

Edits are saved when the user stops: sticky text on blur, position on
pointerup after a drag (not on every keystroke/mousemove). The frontend keeps
the change visible locally and shows a banner if saving fails.
