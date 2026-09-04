# Agent Extension Pack — Module 5 deliverable

Interview Canvas is not just a whiteboard app; since Module 5 it also ships an
*agent extension pack*: the reusable capabilities that let a coding agent work
in this repo effectively, safely, and repeatably.

## Requirements checklist

| Module 5 requirement | Where | Notes |
|----------------------|-------|-------|
| 1 project instructions file | `AGENTS.md` | commands, rules, documents; loaded into every agent context |
| 1 reusable workflow/skill | `.agents/skills/contract-first-feature/SKILL.md` | the repo's real API-feature procedure |
| (+1 more) reusable workflow | `.agents/skills/review-api-change/SKILL.md` | QA review procedure |
| 1 specialized subagent | `.agents/agents/api-reviewer.md` | isolated QA context; applies `review-api-change`, reports `PASS`/`FAIL` |
| 1 MCP tool/server | `mcp-server/server.py` | scoped tools over contract + running instance (stdlib-only, JSON-RPC/stdio) |
| 1 hook/guardrail | `agent-hooks/check_contract_sync.py` + `install.sh` | blocks commits where `backend/` drifts from `openapi.yaml` |
| 1 small plugin/extension package | `plugins/ai-devtools-agent-pack/` | manifest (`plugin.yaml`) + non-destructive installers |
| 1 permission/security note | `docs/permissions.md` | what each capability can and cannot do |

## Layout

```text
AGENTS.md                          standing project instructions
.claude/ (created by installer)    optional symlinks for Claude Code
.agents/
  README.md                        pack index
  skills/contract-first-feature/SKILL.md
  skills/review-api-change/SKILL.md
  agents/api-reviewer.md
agent-hooks/
  check_contract_sync.py           guardrail (pure logic + git wrapper)
  install.sh                       installs .git/hooks/pre-commit
  README.md
mcp-server/
  server.py                        MCP server (stdio, stdlib-only)
  README.md
plugins/ai-devtools-agent-pack/
  plugin.yaml                      manifest
  install.sh                       wires pack into Claude Code / Hermes
  README.md
docs/
  agent-extension-pack.md          this file
  permissions.md                   security note
  demo.md                          recorded end-to-end demo
```

## How a coding agent uses the pack

1. **Project instructions** — every agent session loads `AGENTS.md`
   automatically (commands, rules, documents).
2. **Skills** — Codex/OpenCode read `.agents/skills/` from the repo root;
   Claude Code reads `.claude/skills/` (create with the plugin installer);
   Hermes reads `~/.hermes/skills` (install with the plugin installer). A
   skill is triggered by its `name`/`description` frontmatter.
3. **Subagents** — `.agents/agents/api-reviewer.md` defines an isolated QA
   role: "Launch api-reviewer to review the current change." The reviewer
   follows `review-api-change` and never edits files.
4. **MCP tools** — register `mcp-server/server.py` as a stdio MCP server
   (`claude mcp add --scope project canvas -- uv run python mcp-server/server.py`);
   Codex and OpenCode have equivalent MCP config.
5. **Guardrails** — `agent-hooks/install.sh` installs a pre-commit hook that
   runs the contract-sync check; CI runs the same checks on PRs.
6. **Plugin** — `plugins/ai-devtools-agent-pack/install.sh` carries all of the
   above into another project/tool.

## The demo loop (docs/demo.md)

The demo ships a real feature — `DELETE /boards/{board_id}` — through the
pack: orchestrator reads instructions → implementer follows
`contract-first-feature` → `api-reviewer` subagent reviews the API change →
MCP tool verifies the contract → the pre-commit guardrail runs on the commit.
`docs/demo.md` records the actual run.
