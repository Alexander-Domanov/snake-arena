# agent-hooks — guardrails for agents and humans

Guardrails make repo rules automatic instead of "please be careful". CI checks
pull requests; these hooks run locally, at commit time, on the same machine
where the agent works.

## What is enforced

| Guardrail | Rule | Blocks? |
|-----------|------|---------|
| `check_contract_sync.py` | A change touching `backend/` must also touch `openapi.yaml` (API changes land in the contract first — AGENTS.md). The reverse direction (contract-only edit) is a warning. | Yes (exit 1) |

The check is a pure function (`check(changed_files)`) plus a thin git wrapper,
so it is unit-tested in `tests/test_agent_hooks.py` without a real git hook.

## Install

```bash
./agent-hooks/install.sh          # writes .git/hooks/pre-commit
./agent-hooks/install.sh --uninstall
```

The pre-commit hook runs the contract-sync check on staged changes and blocks
the commit when the backend drifts from the contract.

## Run manually

```bash
# staged changes (same as the pre-commit hook)
python3 agent-hooks/check_contract_sync.py --staged

# whole feature branch against main
python3 agent-hooks/check_contract_sync.py --base origin/main
```

Exit code 0 = pass/warn, 1 = fail.

## Why a guardrail and not just a rule

The Module 4 lesson is that a green pipeline can be a false green (the
collection hook once skipped every test and CI still reported success). Rules
in AGENTS.md are only as good as the agent's attention; a hook that exits
non-zero and blocks the commit is enforced at the point of action.
