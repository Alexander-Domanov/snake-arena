"""Tests for agent-hooks/check_contract_sync.py (pure guardrail logic)."""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def guardrail():
    import importlib.util

    path = REPO_ROOT / "agent-hooks" / "check_contract_sync.py"
    spec = importlib.util.spec_from_file_location("agent_hooks_guardrail", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backend_change_without_contract_fails(guardrail):
    ok, messages = guardrail.check(["backend/routes.py", "backend/services.py"])
    assert ok is False
    assert any("openapi.yaml" in m and "HIGH" in m for m in messages)


def test_backend_change_with_contract_passes(guardrail):
    ok, messages = guardrail.check(
        ["openapi.yaml", "backend/routes.py", "tests/test_api.py"]
    )
    assert ok is True
    assert not any(m.startswith("HIGH") for m in messages)


def test_contract_only_change_warns_but_passes(guardrail):
    ok, messages = guardrail.check(["openapi.yaml"])
    assert ok is True
    assert any("WARN" in m for m in messages)


def test_docs_and_tests_only_pass(guardrail):
    ok, _ = guardrail.check(["README.md", "docs/testing.md", "tests/test_api.py"])
    assert ok is True


def test_empty_change_set_passes(guardrail):
    ok, messages = guardrail.check([])
    assert ok is True
    assert any("PASS" in m for m in messages)
