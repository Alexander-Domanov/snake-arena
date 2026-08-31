# AI Usage Report — Interview Canvas

Date: 2026-08-31
Project: Interview Canvas — collaborative whiteboard for system design interviews
Stack: HTML/CSS/JS (frontend), FastAPI + SQLAlchemy + SQLite (backend), OpenAPI 3.0, pytest, uv

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
| Tests | Wrote unit and integration tests | `tests/` — 30 tests, all passing |
| Integration | Rewrote the frontend to use the real API, CORS, debugging | Frontend ↔ backend over REST, error handling |
| Git | Committed after every stage | 6 commits, clean history |

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

Plus minor non-bug decisions: system Python 3.9 was too old → uv downloaded a
managed Python 3.11 itself; sqlite was not added to dependencies (stdlib module).

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
7. **Committing after every stage** gives a clean history and rollback points:
   6 commits, each self-contained.

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
| **Total** | **≈ 85%** | **≈ 15%** | Rough estimate by volume and significance of contribution |

The estimate is rough. The human owned the direction (what to build, requirements,
style); the AI owned implementation, verification and debugging. Without solid
requirements and the existing spec, the AI share would have been lower.

---

## 6. Time estimate

**Actual time (measured from file and git commit timestamps):**

- First project file: `product-spec.md` — created 2026-08-31 18:36:37
- Last change: `docs/ai-usage-report.md` — created 2026-08-31 19:03:27;
  last commit `3603df4` — 2026-08-31 19:03:30
- **Total from the first file to the last commit: ≈ 27 minutes**

Stages by commit timestamps:

| Commit | Time | Stage |
|--------|------|-------|
| dc8bad2 | 18:48:59 | Frontend prototype + OpenAPI + .gitignore |
| 8e47d10 | 18:50:35 | Backend (FastAPI + SQLite) |
| 404d07b | 18:56:15 | Tests + AGENTS.md |
| f4a4453, f03f29b | 19:02:04 | Frontend–API integration (CORS, POST/DELETE) |
| 3603df4 | 19:03:30 | AI usage report |

Note on the discrepancy with the earlier estimate: the first version of this
report used a rough "2.5–3 hours" figure — based on the volume of work. Actual
file and commit timestamps give ≈ 27 minutes. The difference is explained by the
fact that timestamps only record when files/commits were created (i.e. the AI
assistant's work in this session). The human's preparation time — thinking,
writing `product-spec.md`, formulating tasks — is not captured by timestamps.

---

## 7. Manual edits

Fields below are for the human to refine. Fill in as needed:

- [x] Adjust the contribution estimate (section 5) if you disagree
- [x] Add real effort figures if measured (section 6 — measured from timestamps, ≈ 27 min)
- [ ] Add the human's preparation time (writing product-spec.md, formulating tasks) — not captured by timestamps
- [ ] Add full prompt texts to section 2
- [ ] Note any decisions the human wants to revisit

---

*Report generated by the AI assistant based on the actual work history
(commits, files, verification results).*
