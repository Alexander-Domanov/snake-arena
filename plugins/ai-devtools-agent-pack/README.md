# ai-devtools-agent-pack

A small, shareable plugin that packages this repo's agent capabilities so they
can be carried into other projects and wired into the agent tool of your
choice — the Module 5 "plugin/extension package" requirement.

## What's inside

| Component | Lives in | Installed as |
|-----------|----------|--------------|
| Reusable skills | `.agents/skills/contract-first-feature`, `.agents/skills/review-api-change` | project `.agents/skills/` (Codex/OpenCode auto-discover) |
| Specialized subagent | `.agents/agents/api-reviewer.md` | project `.agents/agents/` |
| Guardrail hook | `agent-hooks/check_contract_sync.py` | git pre-commit via `agent-hooks/install.sh` |
| MCP server | `mcp-server/server.py` | any stdio MCP client (see `mcp-server/README.md`) |

`plugin.yaml` is the human/CI-readable manifest; `install.sh` performs the
wiring. The installers are non-destructive: they only create/remove symlinks.

## Install

```bash
# see what the pack provides and how each tool discovers it
./plugins/ai-devtools-agent-pack/install.sh list

# Claude Code: make .claude/skills and .claude/agents point at .agents/
./plugins/ai-devtools-agent-pack/install.sh claude

# Hermes Agent: link repo skills into ~/.hermes/skills
./plugins/ai-devtools-agent-pack/install.sh hermes

# remove the symlinks the installer created
./plugins/ai-devtools-agent-pack/install.sh uninstall
```

For Codex / OpenCode nothing needs installing: they read `.agents/` at the
repo root by convention.

## Why package it?

The Module 5 mental model: capabilities that only live in one repo stay
trapped there. A plugin/extension package gives a canonical source
(`plugin.yaml` + scripts) and a repeatable install path, so the same pack can
move across projects and across agent tools without re-authoring.
