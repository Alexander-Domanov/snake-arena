# Permissions and security note — Module 5

Every capability in the agent extension pack is deliberately **scoped**:
it can do a small, named set of things and nothing else. This file is the
Module 5 permission note and the reference for reviewers.

## Capability matrix

| Capability | Can do | Cannot do |
|------------|--------|-----------|
| Skills (SKILL.md files) | Instruct an agent to follow a procedure | Execute anything by themselves; they are text |
| Subagent `api-reviewer` | Read code/docs/tests, run read-only checks (`pytest -m "not integration"`), report `PASS`/`FAIL` | Edit files, commit, push, expand scope (role boundary) |
| MCP server | 4 named tools: read `openapi.yaml` paths, read live `/openapi.json`, check `/healthz`, create a board on a *given* base URL | Shell access, filesystem access beyond the `path` argument of one tool, reading environment/secrets, anything not in `tools/list` |
| Guardrail hook | Inspect staged git file names; exit non-zero to block a commit | Modify files, run network calls, enforce anything not in its rule set |
| Plugin installer | Create/remove symlinks in `.claude/` and `~/.hermes/skills` | Delete user files, install global packages, touch other directories |

## MCP server specifics

- **No secrets**: the server reads no environment variables, no config files
  with credentials, and never echoes request payloads.
- **Read-only by default**: three of four tools only read (contract file or a
  live instance). `canvas_create_board` is the single mutation and exists for
  the demo — it POSTs one board to a base URL you name.
- **Localhost assumption**: default `base_url` is `http://localhost:8000`.
  The server has no authentication and must **not** be exposed on a network
  or pointed at production. If you point it at a remote instance, you are
  giving the agent whatever that instance allows.
- **File tool**: `canvas_contract_paths` accepts a `path` argument (default
  `openapi.yaml`). It only opens and line-scans that one file; treat it as a
  read-only file scanner, and do not run the server from a directory that
  contains secrets you do not want an agent to read.

## Guardrail specifics

- Runs locally on commit, examines **staged file names only** (never file
  contents). Blocking rule: `backend/` changed without `openapi.yaml` → exit
  1. Contract-only change → warning only. It is safe to install on any
  machine and does not touch the network.

## Plugin installer specifics

- Non-destructive by design: only `ln -sfn` / `rm -f` on the specific
  symlinks it created (`.claude/skills`, `.claude/agents`, and repo skills in
  `~/.hermes/skills`, overridable via `HERMES_SKILLS_DIR`). Review
  `install.sh` before running it anywhere.

## Boundaries by convention

- The `api-reviewer` subagent must not edit code; if a change fails review it
  reports the single most important fix and hands it back to the implementer.
- Skills are project-level in this pack; the article's global skills (e.g.
  release automation) are out of scope here.
- No capability in this pack grants the agent credentials or deploy access;
  deploys stay human-triggered (see `docs/deployment.md`).
