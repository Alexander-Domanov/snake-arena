# Demo — Agent Extension Pack in action (Module 5)

Date: 2026-09-04. Branch: `module5/agent-extension-pack`.

This is a record of a **real run**, not a scripted ideal: every command below
was executed, every output is copied from the actual run. The demo ships a
real feature through the pack: `DELETE /boards/{board_id}` with element
cascade.

## The demo loop (as required)

1. The agent reads the project instructions.        → `AGENTS.md` loaded in every agent context
2. A reusable workflow is invoked.                  → implementer subagent followed `.agents/skills/contract-first-feature/SKILL.md`
3. A specialized subagent reviews the API change.   → `api-reviewer` subagent (`.agents/agents/api-reviewer.md`) → `VERDICT: PASS`
4. The agent calls an MCP tool.                     → `mcp-server/server.py`, 4 tools listed, 3 called against a live instance
5. A hook or guardrail checks the action.           → pre-commit contract-sync hook ran on the feature commit
6. The student reviews the final diff.              → this file + the commit `af1dedf`

## Cast

- **Orchestrator** — the main session (this one). Routes work, does not
  implement the feature itself.
- **Implementer subagent** — isolated context (SWE role), dispatched by the
  orchestrator; made file changes only, never committed.
- **Reviewer subagent** — isolated context (`api-reviewer` role definition),
  read-only; reported `PASS`/`FAIL`.
- **MCP server** — `uv run python mcp-server/server.py` (stdlib JSON-RPC over
  stdio), driven by a protocol client (same wire format any MCP client uses).
- **Guardrail** — `agent-hooks/check_contract_sync.py`, installed as the git
  pre-commit hook by `agent-hooks/install.sh`.

Environment note (honest): no headless coding-agent CLI (codex/claude) is
installed on this machine, so the "agent" roles were executed as Hermes
subagents with isolated contexts — the same pattern used for the Module 4
on-call demo. The MCP step was driven by a client process speaking the exact
stdio protocol; registering the same command in Claude Code / Codex would
make a real agent the caller. The git-worktree parallel execution from the
article was not exercised (single feature, sequential PM→SWE→QA flow).

## Step 1 — instructions read

`AGENTS.md` is auto-loaded into agent contexts. The implementer was pointed
at it and at the reusable skill; both were read before any edit.

## Step 2 — reusable workflow invoked (implementer subagent)

Dispatched task (abridged): implement `DELETE /boards/{board_id}` following
`.agents/skills/contract-first-feature/SKILL.md`; contract first; backend
service+route mirroring `delete_element`; tests at unit + integration layers;
no commit.

Implementer report (verified by the orchestrator afterwards):

- `openapi.yaml` — `delete` op under `/boards/{board_id}`: operationId
  `deleteBoard`, 204 + 404 (`#/components/responses/NotFound`).
- `backend/routes.py` — `delete_board` route (uuid annotation, 204,
  `Response`); docstring → "six data endpoints … (plus /healthz)".
- `backend/services.py` — `delete_board(db, board_id)`: 404 → `db.delete` →
  `db.commit()`; elements cascade via ORM `cascade="all, delete-orphan"`.
- `tests/test_api.py` — 5 tests: 204 empty body, cascade, 404, delete-twice
  404, 422 non-uuid.
- `tests/integration/test_crud_postgres.py` — cascade test for CI's Postgres
  job.
- `README.md`, `docs/testing.md` — endpoint count five → six.

Orchestrator verification (self-run, not trusted from the report):

```
$ uv run ruff check backend tests e2e alembic on-call-engineer
All checks passed!
$ uv run pytest -m "not integration" -q
66 passed, 15 deselected, 1 warning in 0.84s
```

## Step 3 — specialized subagent reviews (api-reviewer)

Reviewer followed `.agents/skills/review-api-change/SKILL.md`. Verdict:

```
VERDICT: PASS

Findings:
1. [SEV: low] Feature has no user story/AC in product-spec.md — informational
   (mirrors repo precedent for PATCH /healthz).
2. [SEV: low] SQLite-layer cascade test asserted only board 404, not that
   element endpoints are gone — coverage thin at the unit layer.
3. [SEV: low] openapi.yaml delete op documents only 204/404 (422 for
   malformed id is implicit) — matches existing DELETE /elements convention.
```

The orchestrator acted on finding 2 before merging: the cascade unit test now
also asserts `DELETE /elements/{element_id}` → 404 for each element after the
board is deleted (a real QA-loop fix, then `66 passed` again).

## Step 4 — MCP tool call

Server started on demand; app instance running at `http://127.0.0.1:8010`
(SQLite). Actual protocol exchange (abridged to tool results):

```
initialize -> {'name': 'interview-canvas-mcp', 'version': '0.1.0'}
tools/list -> 4 tools: canvas_contract_paths, canvas_openapi_paths,
              canvas_healthz, canvas_create_board

canvas_contract_paths (file openapi.yaml):
Contract openapi.yaml declares 7 endpoint(s):
  POST    /boards
  GET     /boards/{board_id}
  DELETE  /boards/{board_id}      <- the demo feature, present in the contract
  POST    /boards/{board_id}/elements
  PATCH   /elements/{element_id}
  DELETE  /elements/{element_id}
  GET     /healthz

canvas_openapi_paths (live /openapi.json): 7 endpoint(s), incl.
  DELETE  /boards/{board_id}

canvas_healthz: healthz: status='ok' database='ok'

canvas_create_board -> Created board 668396c3-79ca-4c7a-984b-fe07525107f9
```

Then the feature was exercised over HTTP on the same live instance:

```
added element 52db9ce3-... -> 201
DELETE /boards/{id}          -> 204
GET deleted board            -> 404
DELETE cascade element       -> 404   (cascade worked)
```

## Step 5 — hook/guardrail

The pre-commit hook (installed earlier by `agent-hooks/install.sh`) ran on
the feature commit and reported:

```
Guardrail (contract sync):
  PASS: no API-surface drift detected
```

It passed because `openapi.yaml` and `backend/` were staged together — the
exact situation the guardrail exists to enforce. (Its FAIL path — backend
change without contract — is covered by `tests/test_agent_hooks.py`.)

## Step 6 — final diff reviewed by the student

The whole change is one commit on `module5/agent-extension-pack`:

```
af1dedf feat(api): add DELETE /boards/{board_id} with element cascade
```

Reviewable via the final PR (CI + staging deploy). Everything above is
reproducible: start the pack per `docs/agent-extension-pack.md`, run the MCP
server per `mcp-server/README.md`, and re-run the demo steps in this order.
