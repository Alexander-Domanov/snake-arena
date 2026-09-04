# .agents — Agent Extension Pack (Module 5)

Reusable agent capabilities for this repository, in the portable `.agents`
layout described in the course article
[Coding Agent Building Blocks: Reusable Skills and Specialized Subagents](https://aishippingblog.com/p/coding-agent-building-blocks-reusable).

What lives here:

| Path | Kind | Purpose |
|------|------|---------|
| `skills/contract-first-feature/SKILL.md` | reusable workflow | Implement an API feature the way this repo expects: contract (`openapi.yaml`) first, then backend, tests, frontend, checks, commit |
| `skills/review-api-change/SKILL.md` | reusable workflow | Review an API change against the contract and the test suite; output `PASS`/`FAIL` with file:line evidence |
| `agents/api-reviewer.md` | specialized subagent | QA-style reviewer that runs in a separate context and applies `review-api-change` |

## Conventions (frontmatter)

Skills and agents are plain Markdown with a YAML frontmatter block:

```yaml
---
name: <lowercase-hyphen-name>
description: <short, self-contained trigger; when to use this capability>
---
```

Anything after the frontmatter is free-form instructions the agent should
follow. Supporting files (scripts, references) may sit next to `SKILL.md` in
the same directory.

## How a coding agent discovers these

- **Codex / OpenCode / generic agents**: project skills live in `.agents/`
  at the repository root — they are discovered automatically.
- **Claude Code**: reads `.claude/skills/` and `.claude/agents/`. Symlink
  (recommended by the article) or copy:
  ```bash
  ln -s ../../.agents/skills .claude/skills
  ln -s ../../.agents/agents .claude/agents
  ```
- **Hermes Agent**: skills are global (`~/.hermes/skills`). To use a repo
  skill from Hermes, install it (or symlink it) there — the installer in
  `plugins/ai-devtools-agent-pack/` automates this for the whole pack.

## Interaction with AGENTS.md

`AGENTS.md` is the project instructions file (Module 5 requirement 1): it is
always loaded into an agent's context and points at the commands, rules and
documents of this repo. The `.agents` pack adds *reusable procedures*
(skills) and *isolated roles* (subagents) on top of those standing
instructions.

## Demo

`docs/demo.md` records a full run of the pack against a real feature
(`DELETE /boards/{board_id}`): instructions read → skill invoked → subagent
review → MCP tool call → guardrail hook. `docs/agent-extension-pack.md` is
the human-oriented index and `docs/permissions.md` the security note.
