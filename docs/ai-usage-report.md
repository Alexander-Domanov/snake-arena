# AI Usage Report — Interview Canvas

Date: 2026-08-31 (Modules 1–2); updated 2026-09-02 (Module 3); updated 2026-09-03 (Module 4); updated 2026-09-04 (Module 4 finalize)
Project: Interview Canvas — collaborative whiteboard for system design interviews
Stack: HTML/CSS/JS (frontend), FastAPI + SQLAlchemy (backend), OpenAPI 3.0, pytest, uv, Docker, GitHub Actions, Render

This report describes how the AI assistant was used at each stage of the project,
which decisions and issues came up, and what share of the work the AI performed.

---

## 1. How AI was used at each stage

| Stage | AI role | Result |
|-------|---------|--------|
| Specification | Not involved (input data) | `product-spec.md` existed before the work began |
| Frontend prototype | Wrote all the code, verified in a real browser | `frontend/` — index.html, style.css, app.js (Miro-like UI, drag-and-drop, sticky note editing) |
| OpenAPI spec | Designed schemas, wrote and validated the spec | `openapi.yaml` — 4 endpoints, reusable components, examples |
| Backend | Designed structure, implemented, ran the server | `backend/` — FastAPI, SQLAlchemy, SQLite |
| Tests | Wrote unit and integration tests | `tests/` — 32 tests, all passing |
| Frontend tests | Wrote jsdom + node:test coverage of the API contract | `tests/frontend/app.test.mjs` — 10 tests, all passing |
| Integration | Rewrote the frontend to use the real API, CORS, debugging | Frontend ↔ backend over REST, error handling |
| Join-by-link | Implemented joining a board by URL and the share link UI | Frontend opens `?board=<id>` instead of always creating a new board |
| Docs/packaging | README, MIT license, workflow section | `README.md`, `LICENSE` |
| Git | Committed after every stage | 13 commits, clean history |

### Stage details

1. **Specification** — `product-spec.md` (user stories, acceptance criteria,
   non-goals) was provided as-is. The AI used it as the source of requirements.

2. **Frontend prototype** — the AI built a framework-free single-page prototype:
   a board with a dot grid, a toolbar with three buttons, elements (sticky note /
   rectangle / circle), pointer-event drag-and-drop, a delete button, and sticky
   note text editing on double-click. The prototype was verified in a real browser
   (automated run-through: create, drag, edit, delete).

3. **OpenAPI 3.0** — per the user's requirements, Board/Element/ElementCreate
   schemas were described, with reusable components (path parameters, 404/422
   responses) and request/response examples. The spec was validated with the
   official validator plus a custom script checking that examples match schemas.

4. **Backend** — the 4 endpoints from the spec were implemented. Decisions:
   - `backend/schemas.py` was added as a separate pydantic contract layer (it was
     not in the original structure, but separating ORM from API schemas is cleaner);
   - uuid path parameters are validated via the `uuid.UUID` annotation (garbage id → 422);
   - dates are serialized in the format from openapi.yaml (`2026-08-31T10:15:30Z`);
   - `selectinload` for loading elements (protection against DetachedInstanceError);
   - tests are isolated via dependency override (in-memory SQLite).

5. **Tests** — 10 unit tests for models/schemas + 20 API integration tests:
   201/204/404/422, enum, uuid, cascade delete, date format.

6. **Integration** — the frontend was rewritten from mocks to REST: create a board
   on page load, POST/DELETE elements, reload the board after every mutation (the
   server is the source of truth), CORS middleware, error banner, 404 console logging.

7. **Git** — the AI committed after each meaningful step (per the AGENTS.md rule).

8. **Frontend tests** — the real `frontend/index.html` + `app.js` are loaded into
   jsdom with a mocked `fetch` (an in-memory fake mirroring openapi.yaml), and the
   contract behavior is verified: create a board on load, add/delete elements with
   the correct payloads, reload after mutations, error handling.

9. **Join-by-link** — the frontend reads `?board=<id>` from the URL on load: if
   present, it calls `GET /boards/{id}` instead of creating a new board; after
   creation the URL is updated to the shareable link (`history.replaceState`), the
   toolbar shows the link plus a "Copy link" button; a 404 on join shows an error
   and falls back to creating a new board. Verified in a real browser (create flow
   and join flow against the running backend).

10. **Docs/packaging** — README with a workflow section and badges, MIT license,
    `DATABASE_URL` made configurable.

---

## 2. Key prompts

Shown briefly (user's wording):

1. "Read product-spec.md. Create a frontend prototype for Interview Canvas…
   plain HTML+CSS+JS, toolbar, drag-and-drop, delete, Miro-like styles, works
   without a server."
2. "Read product-spec.md. Describe the REST API in OpenAPI 3.0 format…
   endpoints, schemas, components, examples, no auth."
3. "Read product-spec.md and openapi.yaml. Implement the backend with FastAPI,
   SQLite and SQLAlchemy… backend/ structure, dependencies via uv, 404/422/201/204,
   tests, update AGENTS.md, verify the server starts and pytest passes, commit
   after every change."
4. "Update the frontend to use the real backend instead of mocks… create a board
   on load, POST/DELETE, error handling (alert/message, 404 to console),
   base URL localhost:8000, add CORS, verify in the browser, commit."
5. "я вот запустил и не могу понять про доску и получение доски" / "а как должно
   быть по ТЗ?" — explaining the board lifecycle and the gap between user story #2
   (join by ID) and its acceptance criteria.
6. "да давай приведем" — implement join-by-link per the spec, add frontend tests,
   update the acceptance criteria checkboxes in product-spec.md.

All prompts were in Russian, with clear requirements and acceptance criteria.

---

## 3. Bugs fixed

| # | Bug | Found when | Cause | Fix |
|---|-----|-----------|-------|-----|
| 1 | Elements collapsed to text size (sticky was ~24px instead of 160x160) | Frontend prototype, browser verification | `.sticky/.rect/.circle` had no width/height in CSS; absolute positioning shrinks to content | Explicit sizes in CSS; positioning via offsetWidth/offsetHeight |
| 2 | 422 error when adding an element | Integration, E2E check | Frontend sent `type: "sticky"` instead of `"sticky_note"` (toolbar keys ≠ API types) | API_TYPE mapping: sticky→sticky_note, rect→rectangle |
| 3 | Error banner showed "[object Object]" | Integration, E2E check | FastAPI returns 422 `detail` as an array; template literal stringified the object | errorDetail helper (msg of the first error) |
| 4 | New elements stacked exactly on top of each other | Integration, E2E check | Cascade counter reset after every board reload | Offset from center computed from `elements.length` (deterministic) |
| 5 | CORS blocked requests from a file:// page | Integration | No middleware on the backend | CORSMiddleware allow_origins=["*"] + preflight OPTIONS verified |
| 6 | (Proactively) DetachedInstanceError during serialization | Backend | Lazy relationship loading after session close | `selectinload` in get_board |
| 7 | Join link "didn't work" — `?board=<id>` opened an empty board | Live check after join-by-link | The browser served a cached old `app.js` (python http.server sends no Cache-Control; Chrome heuristic caching) — the old code always creates a new board and ignores the URL | Hard refresh / incognito; server logs showed GET /boards/{id} → 200 — the new code was already working |

Plus minor non-bug decisions: system Python 3.9 was too old → uv downloaded a
managed Python 3.11 itself; sqlite was not added to dependencies (stdlib module);
"Address already in use" when starting uvicorn — a leftover dev server was already
on port 8000, not a code issue.

---

## 4. Lessons learned

1. **The contract is the source of truth, but it must be honored literally.**
   openapi.yaml says `sticky_note`, but the frontend sent `sticky`. A spec does not
   protect against typos — enum validation and E2E tests do.
2. **E2E verification in a real browser catches what code reading misses.**
   Bugs 1–4 were found by an automated scenario run, not by static analysis.
   "Verified, not just written" saves time.
3. **The server is the source of truth: keep the client dumb.** After every
   mutation, reload the board from the server. Simpler than syncing local state,
   and it automatically picks up changes from other participants (important for
   the future WebSocket module).
4. **Separate layers: pydantic schemas ≠ ORM models.** A dedicated `schemas.py`
   lets you change the API contract without touching models and vice versa.
5. **Design error behavior deliberately.** 404 → console log (quiet degradation),
   server down → visible banner. Different behavior for different error classes is
   a conscious decision, not an accident.
6. **Document API limitations instead of masking them.** Dragging and sticky note
   text edits live only in the DOM because the API has no update endpoint. This is
   stated explicitly — the next step (PATCH) is obvious.
   *(Implemented later as `PATCH /elements/{element_id}` — persistent editing;
   see the Module 3 addendum, section 8.4.)*
7. **Committing after every stage** gives a clean history and rollback points:
   13 commits, each self-contained.
8. **Static dev servers + browser cache can fake a broken frontend.** python
   http.server sends no Cache-Control, so Chrome heuristically caches app.js; after
   an edit, an old tab keeps running the stale code. Before concluding the code is
   broken, verify the served file (hard refresh, incognito, or check the actual
   HTTP responses).

---

## 5. AI and human contribution estimate

| Stage | AI | Human | Comment |
|-------|----|-------|---------|
| Specification | 0% | 100% | product-spec.md created by the human before the session |
| Frontend prototype | 90% | 10% | Requirements and style (Miro) — human, code — AI |
| OpenAPI spec | 90% | 10% | Endpoint structure set by the human, schemas/validation — AI |
| Backend | 90% | 10% | File structure from the spec, implementation — AI |
| Tests | 95% | 5% | Written and run by AI |
| Integration | 85% | 15% | Detailed requirements + CORS instruction — human, debugging — AI |
| Frontend tests | 95% | 5% | Written and run by AI |
| Join-by-link | 90% | 10% | Requirement (join per the spec) — human, implementation — AI |
| Docs/packaging | 80% | 20% | Content generated by AI, reviewed by human |
| **Total** | **≈ 85%** | **≈ 15%** | Rough estimate by volume and significance of contribution |

The estimate is rough. The human owned the direction (what to build, requirements,
style); the AI owned implementation, verification and debugging. Without solid
requirements and the existing spec, the AI share would have been lower.

---

## 6. Time estimate

**Actual time (measured from file and git commit timestamps):**

- First project file: `product-spec.md` — created 2026-08-31 18:36:37
- Last change: commit `740414d` (join-by-link) — 2026-08-31 19:43:40
- **Total from the first file to the last commit: ≈ 67 minutes**

Stages by commit timestamps:

| Commit | Time | Stage |
|--------|------|-------|
| dc8bad2 | 18:48:59 | Frontend prototype + OpenAPI + .gitignore |
| 8e47d10 | 18:50:35 | Backend (FastAPI + SQLite) |
| 404d07b | 18:56:15 | Tests + AGENTS.md |
| f4a4453, f03f29b | 19:02:04 | Frontend–API integration (CORS, POST/DELETE) |
| 3603df4 | 19:03:30 | AI usage report (first version) |
| b84942e, f025bd1 | 19:06–19:07 | AI usage report (time measured, English) |
| e4f7ac7 | 19:10:28 | README + DATABASE_URL |
| 871c2ab | 19:15:24 | Frontend tests (jsdom + node:test) |
| 3e8a735, e241704 | 19:25:26 | MIT license + README workflow/badges |
| 740414d | 19:43:40 | Join-by-link (?board=<id>) + share link |

Note on the discrepancy with the earlier estimate: the first version of this
report used a rough "2.5–3 hours" figure — based on the volume of work. Actual
file and commit timestamps give ≈ 27 minutes. The difference is explained by the
fact that timestamps only record when files/commits were created (i.e. the AI
assistant's work in this session). The human's preparation time — thinking,
writing `product-spec.md`, formulating tasks — is not captured by timestamps.

---

## 8. Module 3 — test, containerize, deploy (addendum, 2026-09-01)

### 8.1 How AI was used

| Stage | AI role | Result |
|-------|---------|--------|
| Same-origin frontend | Rewrote API paths from absolute localhost to relative (single-origin deploy) | `frontend/app.js` |
| Static serving | Served `frontend/` from FastAPI (no Node build, one container) | `backend/main.py` |
| Health endpoint | Added `/healthz` contract-first (openapi.yaml → backend → tests) | `backend/routes.py`, tests |
| Migrations | Added Alembic initial migration, runs on startup/entrypoint | `alembic/`, `docker-entrypoint.sh` |
| Containerization | Multi-stage Dockerfile (uv, no Node stage) + docker-compose (Postgres + app, healthchecks) | `Dockerfile`, `docker-compose.yml` |
| Integration tests | Real Postgres: migrations apply, CRUD persists, healthz reflects DB | `tests/integration/` |
| E2E tests | Playwright two-session board flow against the compose stack | `e2e/test_two_sessions.py` |
| CI | GitHub Actions on every PR: lint (ruff), unit, frontend, integration, e2e, image build | `.github/workflows/ci.yml` |
| Deploy | Render blueprint + deploy workflow staging → production via deploy hooks, smoke /healthz | `render.yaml`, `.github/workflows/deploy.yml` |
| Secrets/docs | GitHub secrets, README + docs/testing.md, deployment.md, release-process.md | docs/ |

### 8.2 Module 3 decisions and issues

- **Multi-stage container, no Node stage.** The frontend is vanilla HTML/CSS/JS
  with no build step, so FastAPI serves the static files. This keeps the image
  small and removes a whole class of build flakiness. The Dockerfile became a
  real two-stage build (uv binary stage + runtime) to match the Module 3
  requirement literally.
- **Migrations run in the container entrypoint** (`alembic upgrade head`), so
  every deploy migrates automatically — no separate deploy-time step.
- **DATABASE_URL normalization.** Render injects a plain `postgresql://` URL,
  but the installed driver is psycopg v3 (`postgresql+psycopg://`). The app
  normalizes the scheme at startup instead of forcing Render-side config.
- **CI needs no secrets** — integration tests use a dedicated `canvas_test`
  DB created/dropped per session; e2e tears the stack down with `-v`.
- **Deploy staging before production** with a guard step: if staging's
  `/healthz` smoke fails, production is not promoted. Manual rollback is done
  in the Render dashboard (previous successful deploy).
- **Bug fixed during CI bring-up:** the frontend job on Node 20 globbed the
  wrong test path and alembic needed the DB URL injected into the container —
  both surfaced by actually running CI, not by reading config.
- **Bug found in a post-hoc audit (false-green CI):** the collection hook in
  `tests/integration/conftest.py` skipped *every* collected test when Postgres
  was unreachable — including unit tests that need no Postgres. The CI "Backend
  unit tests" job (which runs without Postgres) therefore silently skipped all
  34 unit tests and still reported green. Lesson: a green CI is only as good
  as what actually ran; audit job logs for "skipped", not just for failures.
  Fix: the hook now skips only tests carrying the `integration` marker.
- **Verified end-to-end:** after wiring secrets, a push to `main` ran the whole
  workflow — staging deploy hook → healthy → production deploy hook → healthy
  (both `/healthz` returned ok).

### 8.3 Module 3 contribution estimate

| Stage | AI | Human | Comment |
|-------|----|-------|---------|
| Test/containerize/CI/deploy code | 90% | 10% | Direction and Render account/secrets — human; implementation, debugging, verification — AI |
| Deploy ops (Render setup, hook URLs, secrets) | 40% | 60% | Human created environments and pasted hook URLs; AI explained where they live and verified via `gh` |

The Module 3 estimate mirrors the earlier modules: the human decided *what*
(test on the real stack, deploy to Render, staging → production) and supplied
account-level access; the AI implemented, ran the pipelines, and debugged
failures found by real runs.

### 8.4 Persistent editing (PATCH), 2026-09-02

Follow-up feature after the Module 3 deploy: sticky note text edits (on blur)
and drag positions (on pointerup) are persisted via a new `PATCH
/elements/{element_id}` endpoint instead of living only in the DOM.

| Item | What happened |
|------|---------------|
| Contract | `openapi.yaml` first: PATCH path + `ElementUpdate` (optional x/y/text) + examples |
| Backend | `schemas.ElementUpdate`, `services.update_element` (partial via `exclude_unset`; explicit `null` clears text), `routes.patch_element` |
| Frontend | `updateElementOnServer()` on blur and pointerup (not per keystroke/mousemove); local state kept on error, banner/log on failure, no rollback |
| Tests | 6 integration tests on real Postgres, 5 new jsdom tests, E2E extended to edit text + drag and verify persistence after reload |
| **Bug found by E2E** | Real double-click editing was broken: `preventDefault()` on pointerdown suppressed click/dblclick generation, and after `setPointerCapture` the dblclick targets the `.el` node while the listener sat on `.note-body`. jsdom tests masked it (synthetic events); only the real-browser Playwright test caught it. Fix: preventDefault only on real drag start; dblclick listener moved to the element node. |

Deploy note: after the merge, Render kept serving the old code because the
service was attached to branch `module3` (stale), not `main`. The Deploy
workflow reported success anyway — a deploy hook returns 200 immediately and
the `/healthz` smoke test passes against the still-running old instance.
Lesson: a green deploy workflow does not prove new code is live; verify the
deployed artifact (e.g. `/openapi.json`), and keep the platform branch in
sync with the release branch. Fix: fast-forwarded `module3` to `main` and
re-ran the deploy.

### 8.5 Module 4 — DevOps and Observability, 2026-09-03

Work done against the Module 4 article requirements (dev/prod model,
container registry, OpenTelemetry, dashboards, alerting, AI on-call).

| Stage | AI role | Result |
|-------|---------|--------|
| Dev/prod promotion | Researched current deploy.yml, rewrote to dev-auto/prod-manual | PR #7: push → staging only; production via workflow_dispatch with staging-health guard; docs synced |
| Registry decision | Read Render docs (deploying-an-image, deploy hooks `imgURL`, API) to choose GHCR path with facts | PR #8: build-once → GHCR `YYYYMMDD-HHMMSS-sha` tags → imgURL deploys; **closed without merge 2026-09-04** — Git-based deploys kept, GHCR deferred |
| OTel instrumentation | Designed `backend/telemetry.py` (env-gated, resource labels), wired counters into routes | Metrics/traces/logs export over OTLP; 6 new unit tests |
| Observability stack | Wrote `observability/` compose project + provisioning | Collector → Prometheus/Loki/Tempo; Grafana dashboard w/ env+version filters; Alertmanager; verified e2e locally |
| Alerting | Wrote Prometheus alert rule (sustained failures, annotated with service/env/version/owner/dashboard) | Alert fires → Alertmanager active (verified with generated failures) |
| On-call engineer | Wrote `on-call-engineer/poll.py` (poll Alertmanager → headless agent) | Dry-run verified; full loop verified in the bug demo |
| Bug demo | Introduced reproducible bug, then acted as orchestrator for the on-call agent | Bug → alert → on-call agent found root cause, fixed, tested, committed (`c1bb27c`, demo branch) |

Bugs/lessons found during the module:

1. **Prometheus templates have no `default` function** — the alert rule
   initially used `| default "unknown"` and Prometheus refused to start.
2. **Root logger level under uvicorn is WARNING** — INFO log records were
   dropped before the OTel logging handler could export them; raise the root
   level when telemetry is enabled.
3. **OTel global MeterProvider cannot be replaced** — unit tests must install
   one provider for the module and assert metric deltas, not absolutes.
4. **The collector's Prometheus exporter appends unit suffixes** (e.g.
   `_elements`) — instruments are created without `unit` so exported names
   stay predictable for dashboards and alert rules.
5. **Render git-backed services cannot deploy a specific image tag** — the
   registry migration needs image-backed services created in the dashboard
   (human step; cannot be automated without a Render API key / PAT).
6. **No headless coding-agent CLI installed locally** (codex/claude/opencode
   absent) — the on-call role in the demo was executed by a Hermes subagent
   with the same brief the poller would give a CLI agent.

Deferred by decision (2026-09-04): the GHCR registry migration — PR #8 was
closed without merge; Git-based Render deploys cover the dev/prod model (see
section 8.6).

Human steps still open (platform accounts): choosing/deploying a managed
observability backend for staging+production, and final cleanup of temporary
Render resources.

### 8.6 Module 4 completed (Git-based deployment, observability stack available locally), 2026-09-04

Final decisions closing Module 4:

- **Deployment model: Git-based on Render, kept.** PR #8 (GHCR registry:
  build once → `YYYYMMDD-HHMMSS-sha` tags → imgURL deploys) was closed
  without merge. Staging auto-deploys on every push to `main`; production is
  promoted manually with a staging-`/healthz` guard. This satisfies the
  module's dev/prod goals; the registry migration is deferred and can be
  revisited later.
- **AGENTS.md updated** with commands for the observability stack and the
  on-call poller (plus Documents rows), so future sessions know how to run
  them; the ruff lint scope now includes `on-call-engineer/` (AGENTS.md and
  CI in sync).
- **Observability stack available locally** (`observability/` compose
  project); telemetry is inert without `OTEL_EXPORTER_OTLP_ENDPOINT`, so the
  app runs and deploys unchanged without the stack.
- **Verified:** staging re-deployed and healthy
  (https://interview-canvas-staging.onrender.com — app loads, `/healthz` ok).

Module 4 is complete.

---

## 9. Manual edits

Fields below are for the human to refine. Fill in as needed:

- [x] Adjust the contribution estimate (section 5) if you disagree
- [x] Add real effort figures if measured (section 6 — measured from timestamps, ≈ 27 min)
- [ ] Add the human's preparation time (writing product-spec.md, formulating tasks) — not captured by timestamps
- [ ] Add full prompt texts to section 2
- [ ] Note any decisions the human wants to revisit

---

*Report generated by the AI assistant based on the actual work history
(commits, files, verification results).*
