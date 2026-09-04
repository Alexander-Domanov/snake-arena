# mcp-server — Interview Canvas MCP server

A small [Model Context Protocol](https://modelcontextprotocol.io) server that
gives a coding agent a **scoped** window into the Interview Canvas app: read
the API contract from the repo or observe a running instance — instead of
handing the agent raw filesystem/shell access to everything.

It is written against the Python **standard library only** (JSON-RPC 2.0 over
stdio, newline-delimited), so it adds no dependencies to `pyproject.toml`.

## Tools

| Tool | What it does | Kind |
|------|--------------|------|
| `canvas_contract_paths` | Lists the HTTP endpoints declared in `openapi.yaml` (repo file, line-scanned — no YAML dependency) | read |
| `canvas_openapi_paths` | Lists live paths from a running app's `/openapi.json` | read |
| `canvas_healthz` | Checks `/healthz` of a running instance (`status` + `database`) | read |
| `canvas_create_board` | Creates a board on a running instance (used by the Module 5 demo) | **mutating** — dev/demo only, see `docs/permissions.md` |

Tools default to `http://localhost:8000`; every tool accepts a `base_url`
argument.

## Run

```bash
uv run python mcp-server/server.py
```

The server speaks MCP on stdin/stdout — do not run it in a terminal expecting
a REPL; it waits for MCP client messages.

## Wire it to a coding agent

Claude Code (project-scoped):

```bash
claude mcp add --scope project canvas -- uv run python mcp-server/server.py
```

Codex / OpenCode (or any stdio MCP client) — register the same command in the
tool's MCP config. Generic smoke test without a client:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"canvas_contract_paths","arguments":{}}}' \
  | uv run python mcp-server/server.py
```

## Design notes

- **Scoped by construction**: the server exposes four narrow tools, not a
  shell. This is the Module 5 lesson — give an agent a scoped tool surface,
  not everything.
- **Stdlib-only**: no `mcp` SDK, no `pyyaml` — the YAML contract is read with
  a small indentation scanner that only needs the `paths:` section shape.
  That keeps `uv sync` unchanged and the unit tests dependency-free.
- **Protocol subset**: `initialize`, `ping`, `tools/list`, `tools/call`;
  notifications are accepted and ignored. Enough for real MCP clients and for
  the protocol tests in `tests/test_mcp_server.py`.

## Tests

```bash
uv run pytest tests/test_mcp_server.py -q
```
