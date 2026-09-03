# Observability stack (Module 4)

A separate Docker Compose project that collects **metrics, traces and logs**
from Interview Canvas through one OpenTelemetry Collector and stores them in
Prometheus, Tempo and Loki, with Grafana for dashboards and Alertmanager for
alerting.

Run from the repo root:

```bash
docker compose -f observability/docker-compose.yml up -d --build
```

Start the app with telemetry enabled (pointing at the collector):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
ENVIRONMENT=development \
uv run uvicorn backend.main:app --reload
```

Then open the app, create a board, add a sticky note / shape. Watch it appear:

| Service | URL | Notes |
|---------|-----|-------|
| Grafana | http://localhost:3000 | admin / admin; dashboard "Interview Canvas Overview" |
| Prometheus | http://localhost:9090 | metrics, alert rules |
| Alertmanager | http://localhost:9093 | alert API for the on-call poller |
| OTel Collector | http://localhost:4318 | OTLP HTTP ingest |
| Loki | http://localhost:3100 | logs |
| Tempo | http://localhost:3200 | traces |

Layout:

```text
observability/
├── docker-compose.yml        separate compose project (name: interview-canvas-observability)
├── otel-collector.yaml       OTLP in → Prometheus/Tempo/Loki out
├── prometheus.yml            scrapes the collector's :8889 endpoint
├── prometheus/rules/alerting.yml   CanvasElementCreationFailures alert
├── alertmanager.yml          receives alerts (no real channel; API polled by on-call-engineer/)
├── loki-config.yaml
├── tempo-config.yaml
└── grafana/
    ├── provisioning/         datasources + dashboard provider (auto-loaded)
    └── dashboards/canvas-overview.json   metrics dashboard, filter by env/version
```

Telemetry is enabled in the app only when `OTEL_EXPORTER_OTLP_ENDPOINT` is
set, so running the app without the stack costs nothing (see
`backend/telemetry.py`).

Tear down:

```bash
docker compose -f observability/docker-compose.yml down -v
```
