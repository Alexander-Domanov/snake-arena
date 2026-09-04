"""Tests for mcp-server/server.py.

The server is stdlib-only, so these tests are dependency-free: they load the
module by path (the directory name `mcp-server` cannot be imported as a
package) and exercise both the JSON-RPC dispatch layer directly and the real
stdio protocol through a subprocess.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / "mcp-server" / "server.py"


@pytest.fixture(scope="module")
def server():
    spec = importlib.util.spec_from_file_location("mcp_server_under_test", SERVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# JSON-RPC dispatch layer
# ---------------------------------------------------------------------------


def test_initialize(server):
    resp = server.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    assert resp["id"] == 1
    assert resp["result"]["protocolVersion"] == server.PROTOCOL_VERSION
    assert resp["result"]["capabilities"]["tools"]["listChanged"] is False
    assert resp["result"]["serverInfo"]["name"] == server.SERVER_NAME


def test_ping(server):
    resp = server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert resp == {"jsonrpc": "2.0", "id": 2, "result": {}}


def test_notifications_are_ignored(server):
    assert (
        server.handle_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        is None
    )


def test_tools_list_exposes_the_scoped_toolset(server):
    resp = server.handle_message(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}
    )
    names = [tool["name"] for tool in resp["result"]["tools"]]
    assert names == [
        "canvas_contract_paths",
        "canvas_openapi_paths",
        "canvas_healthz",
        "canvas_create_board",
    ]
    # every tool documents its arguments
    for tool in resp["result"]["tools"]:
        assert tool["inputSchema"]["type"] == "object"


def test_tools_call_unknown_tool_returns_error(server):
    resp = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "nope", "arguments": {}},
        }
    )
    assert resp["error"]["code"] == -32602
    assert "Unknown tool" in resp["error"]["message"]


def test_tools_call_invalid_arguments_returns_error(server):
    resp = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "canvas_healthz", "arguments": "not-an-object"},
        }
    )
    assert resp["error"]["code"] == -32602


def test_unknown_method_returns_error(server):
    resp = server.handle_message(
        {"jsonrpc": "2.0", "id": 6, "method": "bogus/method"}
    )
    assert resp["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# Tool behaviour
# ---------------------------------------------------------------------------


def test_contract_paths_lists_real_repo_endpoints(server):
    result = server.tool_contract_paths(str(REPO_ROOT / "openapi.yaml"))
    assert result["isError"] is False
    text = result["content"][0]["text"]
    for expected in [
        "POST    /boards",
        "GET     /boards/{board_id}",
        "PATCH   /elements/{element_id}",
        "DELETE  /elements/{element_id}",
    ]:
        assert expected in text, f"contract should declare {expected}"


def test_contract_paths_missing_file_is_error(server, tmp_path):
    result = server.tool_contract_paths(str(tmp_path / "missing.yaml"))
    assert result["isError"] is True


def test_healthz_unreachable_instance_is_clean_error(server):
    # Port 1 refuses connections instantly on every platform.
    result = server.tool_healthz(base_url="http://127.0.0.1:1")
    assert result["isError"] is True
    assert "ERROR" in result["content"][0]["text"]


# ---------------------------------------------------------------------------
# Real stdio protocol (subprocess)
# ---------------------------------------------------------------------------


def test_stdio_protocol_end_to_end():
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "canvas_contract_paths", "arguments": {}},
        },
    ]
    proc = subprocess.run(
        [sys.executable, str(SERVER_PATH)],
        input="\n".join(json.dumps(m) for m in messages) + "\n",
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    # initialize, tools/list, tools/call — the notification produces no reply
    assert [line["id"] for line in lines] == [1, 2, 3]
    assert lines[0]["result"]["serverInfo"]["name"] == "interview-canvas-mcp"
    tool_names = [t["name"] for t in lines[1]["result"]["tools"]]
    assert "canvas_contract_paths" in tool_names
    text = lines[2]["result"]["content"][0]["text"]
    assert "openapi.yaml declares" in text
    assert "DELETE  /elements/{element_id}" in text
