"""Unit tests for the OpenTelemetry application metrics.

The tests install one in-memory MeterProvider for the whole module (the OTel
API does not allow replacing a global MeterProvider once set), drive the API
with the same TestClient + in-memory DB fixture as ``test_api.py``, and assert
on metric *deltas* so earlier tests' cumulative counters do not interfere.
Resource attributes (service name / version / environment) are asserted too —
they are what Grafana filters by.
"""
import pytest
from fastapi.testclient import TestClient
from opentelemetry import metrics as otel_metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import telemetry
from backend.database import Base, get_db
from backend.main import app

MISSING_UUID = "00000000-0000-0000-0000-000000000000"

RESOURCE = {
    "service.name": "interview-canvas",
    "service.version": "0.1.0",
    "deployment.environment": "test",
}


@pytest.fixture(scope="module")
def reader():
    """One in-memory MeterProvider for the whole module (global, non-replaceable)."""
    metric_reader = InMemoryMetricReader()
    provider = MeterProvider(
        resource=Resource.create(RESOURCE),
        metric_readers=[metric_reader],
    )
    otel_metrics.set_meter_provider(provider)
    return metric_reader


@pytest.fixture()
def client():
    """App wired to an isolated in-memory DB via dependency override."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_active_registry():
    """Keep the in-process active-board registry isolated between tests."""
    telemetry._active_since.clear()
    telemetry._last_active_reported = 0
    yield


def metric_sum(reader, name, attributes=None) -> int:
    """Current cumulative sum of the metric ``name`` (0 when not present)."""
    data = reader.get_metrics_data()
    if data is None:
        return 0
    total = 0
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                if metric.name == name:
                    for point in metric.data.data_points:
                        if attributes is None or point.attributes == attributes:
                            total += point.value
    return total


def resource_attributes(reader) -> dict:
    data = reader.get_metrics_data()
    if data is None or not data.resource_metrics:
        return {}
    return dict(data.resource_metrics[0].resource.attributes)


# ---- telemetry gating ----

def test_disabled_without_otlp_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert telemetry.is_enabled() is False
    assert telemetry.setup_telemetry(app=None, engine=None) is False


def test_enabled_with_otlp_endpoint(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    assert telemetry.is_enabled() is True


# ---- application metrics ----

def test_boards_and_elements_are_counted(client, reader):
    boards_before = metric_sum(reader, "canvas_boards_created")
    elements_before = metric_sum(reader, "canvas_elements_created")

    board = client.post("/boards", json={"name": "Rate limiter"}).json()
    client.post(
        f"/boards/{board['id']}/elements",
        json={"type": "sticky_note", "x": 1, "y": 2, "width": 100, "height": 100},
    )
    client.post(
        f"/boards/{board['id']}/elements",
        json={"type": "circle", "x": 3, "y": 4, "width": 50, "height": 50},
    )

    assert metric_sum(reader, "canvas_boards_created") - boards_before == 1
    elements_after = metric_sum(reader, "canvas_elements_created")
    assert elements_after - elements_before == 2
    assert metric_sum(reader, "canvas_elements_created", {"type": "sticky_note"}) == 1
    assert metric_sum(reader, "canvas_elements_created", {"type": "circle"}) == 1
    assert metric_sum(reader, "canvas_element_creation_failures") == 0


def test_element_creation_failures_are_counted(client, reader):
    failures_before = metric_sum(
        reader, "canvas_element_creation_failures", {"reason": "board_not_found"}
    )

    r = client.post(
        f"/boards/{MISSING_UUID}/elements",
        json={"type": "circle", "x": 0, "y": 0, "width": 10, "height": 10},
    )
    assert r.status_code == 404

    assert (
        metric_sum(
            reader, "canvas_element_creation_failures", {"reason": "board_not_found"}
        )
        - failures_before
        == 1
    )


def test_active_boards_reflects_recent_traffic(client, reader):
    active_before = metric_sum(reader, "canvas_active_boards")

    board = client.post("/boards", json={}).json()
    client.get(f"/boards/{board['id']}")

    telemetry._sync_active_boards()
    assert metric_sum(reader, "canvas_active_boards") - active_before == 1

    # A second sync does not double-count.
    telemetry._sync_active_boards()
    assert metric_sum(reader, "canvas_active_boards") - active_before == 1


def test_metrics_carry_resource_labels(client, reader):
    client.post("/boards", json={})
    attrs = resource_attributes(reader)
    # The SDK adds telemetry.sdk.* and service.instance.id on its own; the
    # three labels Grafana filters by must be present with our values.
    assert {k: attrs.get(k) for k in RESOURCE} == RESOURCE
