"""Interview Canvas MCP server — scoped tools for coding agents.

Implements the Model Context Protocol over stdio (newline-delimited JSON-RPC
2.0) using only the Python standard library, so the server needs no new
dependencies. The tools expose a deliberately *scoped* view of the app:
read the API contract from the repo, or observe/health-check a running
instance. One tool (canvas_create_board) is mutating and exists only for the
Module 5 demo — see docs/permissions.md.

Protocol subset implemented: initialize, ping, tools/list, tools/call, and
notifications (ignored, no response). Transport framing for stdio MCP is one
JSON object per line, written to stdout; logs must go to stderr.

Usage:
    uv run python mcp-server/server.py

Client wiring examples (see mcp-server/README.md):
    claude mcp add --scope project canvas -- uv run python mcp-server/server.py
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from typing import Any

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "interview-canvas-mcp"
SERVER_VERSION = "0.1.0"
DEFAULT_BASE_URL = "http://localhost:8000"

_METHOD_LINE = re.compile(r"^\s{4}(get|post|put|patch|delete|head|options):\s*$")
_PATH_LINE = re.compile(r"^\s{2}(/\S+):\s*$")
_SUMMARY_LINE = re.compile(r"^\s{6}summary:\s*(.+)$")
_TOP_LEVEL = re.compile(r"^\S.*:$")

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def _http_json(method: str, url: str, body: str | None = None) -> tuple[Any, str]:
    """Return (parsed_json, error_text). error_text is '' on success."""
    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/json")
    data = None
    if body is not None:
        data = body.encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}, ""
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return {}, f"ERROR: cannot reach {url}: {exc}"


def tool_contract_paths(path: str = "openapi.yaml") -> dict[str, Any]:
    """List the HTTP endpoints declared in the repo's openapi.yaml.

    Uses a small line scanner (no YAML dependency): it only needs the
    indentation structure of the paths section.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError as exc:
        return {"content": [{"type": "text", "text": f"ERROR: {exc}"}], "isError": True}

    endpoints: list[str] = []
    in_paths = False
    current_path = ""
    for idx, line in enumerate(lines):
        stripped = line.rstrip("\n")
        if stripped.strip() == "" or stripped.lstrip().startswith("#"):
            continue
        if not in_paths:
            if stripped == "paths:":
                in_paths = True
            continue
        if not stripped.startswith(" ") and stripped.endswith(":"):
            break  # left the paths section
        m_path = _PATH_LINE.match(stripped)
        if m_path and not stripped.startswith(" " * 4):
            current_path = m_path.group(1)
            continue
        m_method = _METHOD_LINE.match(stripped)
        if m_method and current_path:
            summary = ""
            if idx + 1 < len(lines):
                m_summary = _SUMMARY_LINE.match(lines[idx + 1].rstrip("\n"))
                if m_summary:
                    summary = m_summary.group(1).strip()
            endpoints.append(
                f"{m_method.group(1).upper():7} {current_path}"
                + (f" — {summary}" if summary else "")
            )
    if not endpoints:
        return {
            "content": [
                {"type": "text", "text": f"No endpoints found in {path} (paths section missing?)"}
            ],
            "isError": True,
        }
    text = f"Contract {path} declares {len(endpoints)} endpoint(s):\n" + "\n".join(endpoints)
    return {"content": [{"type": "text", "text": text}], "isError": False}


def tool_openapi_paths(base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    """List live API paths from a running app's /openapi.json."""
    data, err = _http_json("GET", f"{base_url.rstrip('/')}/openapi.json")
    if err:
        return {"content": [{"type": "text", "text": err}], "isError": True}
    paths = data.get("paths", {})
    rows: list[str] = []
    for path, methods in paths.items():
        for method, spec in methods.items():
            if method == "parameters":
                continue
            op_id = spec.get("operationId", "")
            rows.append(f"{method.upper():7} {path}" + (f"  [{op_id}]" if op_id else ""))
    text = f"Live /openapi.json declares {len(rows)} endpoint(s):\n" + "\n".join(sorted(rows))
    return {"content": [{"type": "text", "text": text}], "isError": False}


def tool_healthz(base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    """Check /healthz of a running app instance (status + database)."""
    data, err = _http_json("GET", f"{base_url.rstrip('/')}/healthz")
    if err:
        return {"content": [{"type": "text", "text": err}], "isError": True}
    return {
        "content": [
            {
                "type": "text",
                "text": f"healthz: status={data.get('status')!r} database={data.get('database')!r}",
            }
        ],
        "isError": False,
    }


def tool_create_board(base_url: str = DEFAULT_BASE_URL, name: str | None = None) -> dict[str, Any]:
    """Create a board on a running instance (demo/mutation tool — see permissions.md)."""
    body = json.dumps({"name": name}) if name else "{}"
    data, err = _http_json("POST", f"{base_url.rstrip('/')}/boards", body=body)
    if err:
        return {"content": [{"type": "text", "text": err}], "isError": True}
    board_id = data.get("id", "?")
    return {
        "content": [
            {
                "type": "text",
                "text": f"Created board {board_id}\n"
                f"Join URL: {base_url.rstrip('/')}/?board={board_id}",
            }
        ],
        "isError": False,
    }


TOOLS: list[dict[str, Any]] = [
    {
        "name": "canvas_contract_paths",
        "description": "List the HTTP endpoints declared in openapi.yaml (repo file). "
        "Use to verify a change updated the contract.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "default": "openapi.yaml",
                    "description": "Path to openapi.yaml, relative to the repo root",
                }
            },
        },
    },
    {
        "name": "canvas_openapi_paths",
        "description": "List live API paths from a running app's /openapi.json.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_url": {
                    "type": "string",
                    "default": DEFAULT_BASE_URL,
                    "description": "Base URL of a running Interview Canvas instance",
                }
            },
        },
    },
    {
        "name": "canvas_healthz",
        "description": "Check /healthz of a running instance (status + database).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_url": {
                    "type": "string",
                    "default": DEFAULT_BASE_URL,
                    "description": "Base URL of a running Interview Canvas instance",
                }
            },
        },
    },
    {
        "name": "canvas_create_board",
        "description": "Create a board on a running instance. Mutating tool — dev/demo only, "
        "see docs/permissions.md.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_url": {
                    "type": "string",
                    "default": DEFAULT_BASE_URL,
                    "description": "Base URL of a running Interview Canvas instance",
                },
                "name": {
                    "type": "string",
                    "description": "Optional board name",
                },
            },
        },
    },
]

_TOOL_FUNCS: dict[str, Any] = {
    "canvas_contract_paths": tool_contract_paths,
    "canvas_openapi_paths": tool_openapi_paths,
    "canvas_healthz": tool_healthz,
    "canvas_create_board": tool_create_board,
}

# ---------------------------------------------------------------------------
# JSON-RPC / MCP handling
# ---------------------------------------------------------------------------


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_message(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one parsed JSON-RPC message; return the response (None for notifications)."""
    request_id = msg.get("id")
    method = msg.get("method")

    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )
    if isinstance(method, str) and method.startswith("notifications/"):
        return None
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = msg.get("params") or {}
        tool_name = str(params.get("name") or "")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return _error(request_id, -32602, f"Invalid arguments for {tool_name}: not an object")
        fn = _TOOL_FUNCS.get(tool_name)
        if fn is None:
            return _error(request_id, -32602, f"Unknown tool: {tool_name}")
        try:
            return _result(request_id, fn(**arguments))
        except TypeError as exc:
            return _error(request_id, -32602, f"Invalid arguments for {tool_name}: {exc}")
    return _error(request_id, -32601, f"Method not found: {method}")


def run_stdio() -> None:
    """Read newline-delimited JSON-RPC from stdin and write responses to stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f'{{"jsonrpc":"2.0","id":null,"error":{{"code":-32700,"message":"Parse error: {exc}"}}}}')
            continue
        if not isinstance(msg, dict):
            continue
        response = handle_message(msg)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    try:
        run_stdio()
    except KeyboardInterrupt:
        sys.exit(130)
