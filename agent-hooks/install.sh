#!/usr/bin/env bash
# Install/uninstall the repo's git guardrail hooks.
#
# Hooks live in .git/hooks (not versioned), so this installer copies the
# versioned hook scripts from agent-hooks/ into .git/hooks/.
#
# Usage:
#   ./agent-hooks/install.sh          # install pre-commit hook
#   ./agent-hooks/install.sh --uninstall
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
SRC_DIR="$REPO_ROOT/agent-hooks"
HOOK_NAME="pre-commit"

if [[ "${1:-}" == "--uninstall" ]]; then
  rm -f "$HOOKS_DIR/$HOOK_NAME"
  echo "Removed $HOOKS_DIR/$HOOK_NAME"
  exit 0
fi

cat > "$HOOKS_DIR/$HOOK_NAME" <<'HOOK'
#!/usr/bin/env bash
# Installed by agent-hooks/install.sh — repo guardrails, run on every commit.
# Re-run the installer after changing agent-hooks/ scripts.
set -uo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
python3 "$REPO_ROOT/agent-hooks/check_contract_sync.py" --staged
HOOK

chmod +x "$HOOKS_DIR/$HOOK_NAME"
echo "Installed $HOOKS_DIR/$HOOK_NAME"
echo "Hook content: ruff + guardrails are agent-facing; this hook enforces contract sync."
