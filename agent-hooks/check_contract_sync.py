#!/usr/bin/env python3
"""Guardrail: keep the OpenAPI contract and the backend implementation in sync.

The repo rule (AGENTS.md) is "all API changes must be reflected in
openapi.yaml first". This hook makes the rule automatic instead of relying on
the agent's memory:

  - backend/ changed, openapi.yaml did not  -> FAIL (blocks the commit)
  - openapi.yaml changed, backend/ did not  -> WARN (contract-only edit is
    legitimate, e.g. documentation; an implementation usually follows)
  - anything else                            -> PASS

Usage:
    python agent-hooks/check_contract_sync.py --staged     # pre-commit use
    python agent-hooks/check_contract_sync.py --base main   # diff main...HEAD

Exit code 0 = pass/warn, 1 = fail.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Iterable

CONTRACT_FILE = "openapi.yaml"
BACKEND_PREFIX = "backend"


def check(changed_files: Iterable[str]) -> tuple[bool, list[str]]:
    """Return (ok, messages) for a set of changed paths.

    Pure function so the guardrail is unit-testable without git.
    """
    changed = set(changed_files)
    backend_changed = any(
        p == BACKEND_PREFIX or p.startswith(BACKEND_PREFIX + "/") for p in changed
    )
    contract_changed = CONTRACT_FILE in changed

    messages: list[str] = []
    if backend_changed and not contract_changed:
        messages.append(
            f"HIGH: {BACKEND_PREFIX}/ changed but {CONTRACT_FILE} did not — API changes "
            f"must land in {CONTRACT_FILE} first (AGENTS.md rule). "
            "Add the contract change, or make the reason it is unnecessary explicit."
        )
        return False, messages
    if contract_changed and not backend_changed:
        messages.append(
            f"WARN: {CONTRACT_FILE} changed but {BACKEND_PREFIX}/ did not — "
            "if this is a real API change, the implementation is missing."
        )
        return True, messages
    messages.append("PASS: no API-surface drift detected")
    return True, messages


def _git_changed_files(base: str | None, head: str | None, staged: bool) -> list[str]:
    if staged:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
    elif base:
        cmd = ["git", "diff", "--name-only", "--diff-filter=ACM", f"{base}...{head or 'HEAD'}"]
    else:
        cmd = ["git", "diff", "--name-only", "--diff-filter=ACM"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return [line for line in out.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--staged", action="store_true", help="check staged changes (pre-commit)")
    group.add_argument(
        "--base",
        metavar="REF",
        help="check the diff between REF and HEAD (e.g. origin/main)",
    )
    args = parser.parse_args(argv)

    changed = _git_changed_files(base=args.base, head=None, staged=args.staged)
    if not changed:
        print("Guardrail: no changed files")
        return 0

    ok, messages = check(changed)
    print("Guardrail (contract sync):")
    for msg in messages:
        print(f"  {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
