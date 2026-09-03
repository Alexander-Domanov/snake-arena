# On-Call Engineer (Module 4)

A proof-of-concept that turns the observability alerts into an actual
response: a small poller watches Alertmanager and, when an alert fires, starts
a headless coding agent that investigates the root cause, fixes the bug and
commits the fix.

This mirrors the article's design (an SNS/Lambda-style trigger that starts a
container job running Codex/Claude in headless mode) in the simplest local
form: **poll Alertmanager every minute → pass the alert to an agent CLI**.

## Usage

```bash
# Dry run: print what would be sent to the agent (no agent required)
uv run on-call-engineer/poll.py --once

# Real mode: delegate every new firing alert to a headless agent
ONCALL_AGENT_CMD='codex exec --skip-git-repo-check {prompt}' \
  uv run on-call-engineer/poll.py

# Custom Alertmanager endpoint
ALERTMANAGER_URL=http://localhost:9093 uv run on-call-engineer/poll.py
```

The `{prompt}` placeholder is replaced with a self-contained on-call brief
built from the alert: service, environment, deployed version, owner, dashboard
URL and the alert description. The prompt tells the agent to reproduce the
failure, fix the smallest thing, run the backend tests and commit — and to
explain instead of changing code when the alert is a false positive.

Already-handled alerts are remembered in `.handled-alerts.json` (gitignored),
so a restart does not re-trigger old alerts.

## How it fits together

```text
Prometheus alert rule (rate of canvas_element_creation_failures > 0 for 2m)
   └─► Alertmanager (:9093)
         └─► on-call-engineer/poll.py (every 60s)
               └─► headless agent (ONCALL_AGENT_CMD) with the alert brief
                     └─► reads code, reproduces, fixes, runs tests, commits
```

The observability stack (and the alert rule) lives in `observability/`.

## Demo recipe (the article's "introduce a bug" step)

1. Start the stack: `docker compose -f observability/docker-compose.yml up -d`.
2. Start the app with `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`.
3. Introduce a reproducible bug in element creation (branch).
4. Generate failing requests for > 2 minutes (the alert needs `rate > 0 for
   2m`), e.g.:
   ```bash
   while true; do
     curl -s -o /dev/null -X POST \
       http://localhost:8001/boards/00000000-0000-0000-0000-000000000000/elements \
       -H 'Content-Type: application/json' \
       -d '{"type":"circle","x":0,"y":0,"width":10,"height":10}'
     sleep 5
   done
   ```
5. Watch the poller pick up the alert and the agent fix the bug.
