"""Manifest integrity for plugins/ai-devtools-agent-pack.

The plugin is plain files + a YAML manifest. This test keeps the manifest
honest: every source path it declares must exist in the repo, and the
declared MCP command must point at the real server. No YAML parser needed —
the manifest lines we care about are `source:` / `command:` entries.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "plugins" / "ai-devtools-agent-pack" / "plugin.yaml"
INSTALLER = REPO_ROOT / "plugins" / "ai-devtools-agent-pack" / "install.sh"


@pytest.fixture(scope="module")
def manifest_text() -> str:
    return MANIFEST.read_text(encoding="utf-8")


def test_manifest_exists_and_declares_the_pack(manifest_text):
    assert "name: ai-devtools-agent-pack" in manifest_text
    assert "provides:" in manifest_text
    for component in ["skills:", "agents:", "guardrails:", "mcp:"]:
        assert component in manifest_text


def test_declared_sources_exist(manifest_text):
    sources = re.findall(r"^\s+- source: (\S+)$", manifest_text, re.MULTILINE)
    assert len(sources) >= 4, "expected the four pack components"
    for source in sources:
        assert (REPO_ROOT / source).exists(), f"manifest source missing: {source}"


def test_declared_installer_and_command_exist(manifest_text):
    installer = re.search(r"installer: (\S+)", manifest_text)
    assert installer is not None
    assert (REPO_ROOT / installer.group(1)).exists()

    command = re.search(r"^\s*command: (\S.*)$", manifest_text, re.MULTILINE)
    assert command is not None
    parts = command.group(1).split()
    # "uv run python mcp-server/server.py" -> last token is the server file
    assert (REPO_ROOT / parts[-1]).exists()


def test_installer_is_executable_script():
    assert INSTALLER.exists()
    text = INSTALLER.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env bash")
    assert 'cmd_claude' in text and 'cmd_hermes' in text and 'cmd_uninstall' in text
