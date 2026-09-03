"""OpenTelemetry setup and Interview Canvas application metrics.

Design goals
------------
- **Inert by default.** Telemetry is enabled only when
  ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set (e.g. ``http://localhost:4318`` for
  the local ``observability/`` stack). Without a global MeterProvider the
  OpenTelemetry API returns no-op instruments, so the metric calls sprinkled
  through the routes are free in unit tests, CI and local dev without a
  collector.
- **Never breaks the app.** Every instrumentation step is wrapped: if a piece
  of the SDK fails to initialize, we log a warning and continue serving.
- **Resource attributes become labels.** ``service.name``,
  ``service.version`` and ``deployment.environment`` are attached to every
  metric, trace and log; the OTel Collector copies them into Prometheus
  labels, which is what lets Grafana filter by environment and deployed
  version.

Metrics tracked (Module 4):
- ``canvas_boards_created`` — interview rooms (boards) created [counter]
- ``canvas_elements_created`` — canvas elements created, by ``type`` [counter]
- ``canvas_element_creation_failures`` — element creation failures, by
  ``reason`` [counter]
- ``canvas_active_boards`` — boards with activity in the last 5 minutes
  [updown counter, approximate: no presence/WebSocket layer exists, so a board
  counts as active while its API is being used]
"""
from __future__ import annotations

import logging
import os
import threading
import time

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger("interview_canvas.telemetry")

SERVICE_NAME = "interview-canvas"
SERVICE_VERSION = os.getenv("APP_VERSION", "0.1.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# A board counts as active while it has API traffic within this window.
ACTIVE_WINDOW_SECONDS = 300
_ACTIVE_SYNC_INTERVAL_SECONDS = 30

_meter = metrics.get_meter(SERVICE_NAME, SERVICE_VERSION)

# --- instruments (no-op unless a MeterProvider is installed) ---
boards_created = _meter.create_counter(
    "canvas_boards_created",
    unit="boards",
    description="Interview rooms (boards) created",
)
elements_created = _meter.create_counter(
    "canvas_elements_created",
    unit="elements",
    description="Canvas elements created",
)
element_creation_failures = _meter.create_counter(
    "canvas_element_creation_failures",
    unit="elements",
    description="Canvas element creation failures",
)
active_boards = _meter.create_up_down_counter(
    "canvas_active_boards",
    unit="boards",
    description="Boards with API activity in the last 5 minutes (approximate)",
)

# --- in-process registry of recently active boards ---
_active_lock = threading.Lock()
_active_since: dict[str, float] = {}
_last_active_reported = 0
_setup_lock = threading.Lock()
_setup_done = False


def record_board_activity(board_id: str) -> None:
    """Mark a board as active right now (called on successful board requests)."""
    with _active_lock:
        _active_since[board_id] = time.time()


def _prune_active_boards() -> None:
    now = time.time()
    with _active_lock:
        stale = [
            bid for bid, last_seen in _active_since.items()
            if now - last_seen > ACTIVE_WINDOW_SECONDS
        ]
        for bid in stale:
            _active_since.pop(bid, None)


def _sync_active_boards() -> None:
    """Reconcile the up/down counter with the current registry size."""
    global _last_active_reported
    _prune_active_boards()
    with _active_lock:
        current = len(_active_since)
    delta = current - _last_active_reported
    if delta:
        active_boards.add(delta)
        _last_active_reported = current


def _active_boards_loop() -> None:
    while True:
        time.sleep(_ACTIVE_SYNC_INTERVAL_SECONDS)
        try:
            _sync_active_boards()
        except Exception:  # pragma: no cover - defensive
            logger.warning("active_boards sync failed", exc_info=True)


def is_enabled() -> bool:
    """Telemetry is enabled when an OTLP endpoint is configured."""
    return bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())


def setup_telemetry(app=None, engine=None) -> bool:
    """Configure OTLP exporters + instrumentations. Idempotent, never raises.

    Returns True when telemetry was enabled and configured, False otherwise.
    """
    global _setup_done
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip().rstrip("/")
    if not endpoint:
        return False
    with _setup_lock:
        if _setup_done:
            return True
        _setup_done = True

    resource = Resource.create(
        {
            "service.name": SERVICE_NAME,
            "service.version": SERVICE_VERSION,
            "deployment.environment": ENVIRONMENT,
        }
    )

    try:
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
        )
        trace.set_tracer_provider(tracer_provider)
    except Exception:
        logger.warning("OTel trace provider setup failed", exc_info=True)

    try:
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
            export_interval_millis=10_000,
        )
        metrics.set_meter_provider(
            MeterProvider(resource=resource, metric_readers=[metric_reader])
        )
        # After installing a real provider the instruments above become live.
        threading.Thread(
            target=_active_boards_loop, daemon=True, name="otel-active-boards"
        ).start()
    except Exception:
        logger.warning("OTel metric provider setup failed", exc_info=True)

    try:
        log_provider = LoggerProvider(resource=resource)
        log_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{endpoint}/v1/logs"))
        )
        logging.getLogger().addHandler(
            LoggingHandler(level=logging.INFO, logger_provider=log_provider)
        )
    except Exception:
        logger.warning("OTel log provider setup failed", exc_info=True)

    try:
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
        if engine is not None:
            SQLAlchemyInstrumentor().instrument(engine=engine)
    except Exception:
        logger.warning("OTel instrumentation failed", exc_info=True)

    logger.info(
        "OpenTelemetry enabled: endpoint=%s env=%s version=%s",
        endpoint,
        ENVIRONMENT,
        SERVICE_VERSION,
    )
    return True
