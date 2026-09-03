#!/usr/bin/env python3
"""On-call engineer: poll the observability alert API and wake a coding agent.

Module 4 (the "On-Call Engineer" step): every minute this script asks
Alertmanager for firing alerts; when a new one appears it builds a prompt
from the alert's labels/annotations (service, environment, deployed version,
owner, dashboard URL) and hands it to a headless coding agent.

No agent CLI is hardwired: point ONCALL_AGENT_CMD at your headless agent
(e.g. Codex, Claude Code, OpenCode). The string ``{prompt}`` is replaced with
the generated prompt. When ONCALL_AGENT_CMD is empty/unset the script only
logs the alert and the prompt (dry-run mode) — useful for the demo and for CI.

Usage:
    # dry-run once (print alert details + prompt, run no agent)
    uv run on-call-engineer/poll.py --once

    # poll every minute and delegate to a headless agent
    ONCALL_AGENT_CMD='codex exec --skip-git-repo-check {prompt}' \
        uv run on-call-engineer/poll.py

    # point at a different Alertmanager
    ALERTMANAGER_URL=http://localhost:9093 uv run on-call-engineer/poll.py
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shlex
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

logger = logging.getLogger("oncall")

STATE_FILE = Path(__file__).resolve().parent / ".handled-alerts.json"
ALERTMANAGER_URL = os.getenv("ALERTMANAGER_URL", "http://localhost:9093")
REPO_ROOT = Path(__file__).resolve().parent.parent

ONCALL_PROMPT = """You are the on-call engineer for this repository ({repo}).

An alert just fired:

  alert:      {alertname}
  severity:   {severity}
  service:    {service}
  environment:{environment}
  version:    {version}
  owner:      {owner}
  dashboard:  {dashboard}

Details from the alert:
{description}

Investigate the root cause. Read the code and reproduce the failure.
If you find a real bug, make the smallest correction, run the backend tests,
and commit the fix with a clear message.
If the alert is a false positive, explain why and do not change the code.
"""


def load_handled() -> set[str]:
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text()).get("handled", []))
        except (json.JSONDecodeError, OSError):
            return set()
    return set()


def save_handled(handled: set[str]) -> None:
    STATE_FILE.write_text(json.dumps({"handled": sorted(handled)}, indent=2))


def fetch_alerts() -> list[dict]:
    url = f"{ALERTMANAGER_URL}/api/v2/alerts"
    with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 - local observability API
        return json.loads(resp.read().decode())


def alert_key(alert: dict) -> str:
    labels = alert.get("labels", {})
    return f'{labels.get("alertname", "unknown")}|{labels.get("deployment_environment", "")}|{labels.get("service_version", "")}|{labels.get("fingerprint", alert.get("fingerprint", ""))}'


def build_prompt(alert: dict) -> str:
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    return ONCALL_PROMPT.format(
        repo=REPO_ROOT,
        alertname=labels.get("alertname", "unknown"),
        severity=labels.get("severity", "unknown"),
        service=labels.get("service_name", "unknown"),
        environment=labels.get("deployment_environment", "unknown"),
        version=labels.get("service_version", "unknown"),
        owner=labels.get("owner", annotations.get("owner", "unknown")),
        dashboard=annotations.get("dashboard", "unknown"),
        description=annotations.get("description", "(no description)"),
    )


def run_agent(prompt: str) -> None:
    agent_cmd = os.getenv("ONCALL_AGENT_CMD", "").strip()
    if not agent_cmd:
        logger.warning("ONCALL_AGENT_CMD is not set — dry-run mode, agent NOT started")
        logger.info("Would hand this prompt to the on-call agent:\n%s", prompt)
        return
    if "{prompt}" not in agent_cmd:
        logger.error("ONCALL_AGENT_CMD must contain the {prompt} placeholder")
        return
    cmd = agent_cmd.replace("{prompt}", prompt)
    logger.info("Starting on-call agent: %s", cmd)
    try:
        result = subprocess.run(
            shlex.split(cmd),
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        logger.info("agent exit code: %s", result.returncode)
        if result.stdout:
            logger.info("agent stdout:\n%s", result.stdout[-4000:])
        if result.stderr:
            logger.warning("agent stderr:\n%s", result.stderr[-2000:])
    except subprocess.TimeoutExpired:
        logger.error("on-call agent timed out after 30 minutes")
    except FileNotFoundError as exc:
        logger.error("on-call agent executable not found: %s", exc)


def poll_once() -> list[dict]:
    handled = load_handled()
    alerts = fetch_alerts()
    new_alerts = []
    for alert in alerts:
        if alert.get("status", {}).get("state") != "active":
            continue
        key = alert_key(alert)
        if key in handled:
            continue
        new_alerts.append(alert)
        handled.add(key)
    save_handled(handled)

    for alert in new_alerts:
        labels = alert.get("labels", {})
        logger.info(
            "ALERT %s [%s] env=%s version=%s",
            labels.get("alertname", "unknown"),
            labels.get("severity", "unknown"),
            labels.get("deployment_environment", "unknown"),
            labels.get("service_version", "unknown"),
        )
        prompt = build_prompt(alert)
        run_agent(prompt)
    return new_alerts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=int, default=60, help="poll interval seconds")
    parser.add_argument("--once", action="store_true", help="poll once and exit")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.once:
        poll_once()
        return 0

    logger.info("polling %s every %ss (state: %s)", ALERTMANAGER_URL, args.interval, STATE_FILE)
    while True:
        try:
            poll_once()
        except Exception:
            logger.exception("poll iteration failed")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
