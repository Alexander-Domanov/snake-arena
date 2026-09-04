#!/usr/bin/env bash
# Install the ai-devtools-agent-pack into a coding agent of your choice.
#
# The pack itself is versioned in this repo:
#   .agents/skills/*       reusable workflows (SKILL.md)
#   .agents/agents/*.md    specialized subagents
#   agent-hooks/           guardrail scripts + git-hook installer
#   mcp-server/            MCP server (scoped tools)
#
# Usage:
#   ./plugins/ai-devtools-agent-pack/install.sh list
#   ./plugins/ai-devtools-agent-pack/install.sh claude        # symlink into .claude/
#   ./plugins/ai-devtools-agent-pack/install.sh hermes        # symlink into ~/.hermes/skills
#   ./plugins/ai-devtools-agent-pack/install.sh uninstall     # remove created symlinks
#
# Installers never delete user files: they only create/remove symlinks.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PACK_DIR="$REPO_ROOT/plugins/ai-devtools-agent-pack"

hermes_skills_dir() {
  echo "${HERMES_SKILLS_DIR:-$HOME/.hermes/skills}"
}

cmd_list() {
  echo "ai-devtools-agent-pack provides:"
  echo "  skills:      contract-first-feature, review-api-change"
  echo "  agents:      api-reviewer"
  echo "  guardrails:  agent-hooks/check_contract_sync.py (+ pre-commit installer)"
  echo "  mcp server:  mcp-server/server.py (uv run python mcp-server/server.py)"
  echo
  echo "Discovery:"
  echo "  Codex/OpenCode   .agents/ at repo root — automatic, nothing to do"
  echo "  Claude Code      install.sh claude"
  echo "  Hermes Agent     install.sh hermes"
}

cmd_claude() {
  mkdir -p "$REPO_ROOT/.claude"
  ln -sfn ../.agents/skills "$REPO_ROOT/.claude/skills"
  ln -sfn ../.agents/agents "$REPO_ROOT/.claude/agents"
  echo "Linked .claude/skills and .claude/agents -> .agents/ (Claude Code)"
}

cmd_hermes() {
  local dst
  dst="$(hermes_skills_dir)"
  mkdir -p "$dst"
  for skill in "$REPO_ROOT"/.agents/skills/*/; do
    [ -d "$skill" ] || continue
    ln -sfn "$skill" "$dst/$(basename "$skill")"
    echo "Linked $(basename "$skill") -> $dst/$(basename "$skill")"
  done
  echo "Hermes reads SKILL.md files from $dst. Subagents: copy"
  echo ".agents/agents/*.md into a project .hermes/agents/ dir if your setup supports it."
}

cmd_uninstall() {
  rm -f "$REPO_ROOT/.claude/skills" "$REPO_ROOT/.claude/agents"
  local dst
  dst="$(hermes_skills_dir)"
  for skill in "$REPO_ROOT"/.agents/skills/*/; do
    [ -d "$skill" ] || continue
    rm -f "$dst/$(basename "$skill")"
  done
  echo "Removed symlinks created by this installer (nothing else was touched)."
}

case "${1:-list}" in
  list) cmd_list ;;
  claude) cmd_claude ;;
  hermes) cmd_hermes ;;
  uninstall) cmd_uninstall ;;
  *) echo "Usage: $0 {list|claude|hermes|uninstall}" >&2; exit 1 ;;
esac
