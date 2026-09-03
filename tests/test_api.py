"""Integration tests for the HTTP API (TestClient against the real app)."""
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
DT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

MISSING_UUID = "00000000-0000-0000-0000-000000000000"


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


def create_board(client, name=None):
    body = {"name": name} if name is not None else {}
    return client.post("/boards", json=body)


def add_element(client, board_id, **overrides):
    payload = {"type": "circle", "x": 0, "y": 0, "width": 130, "height": 130}
    payload.update(overrides)
    return client.post(f"/boards/{board_id}/elements", json=payload)


# ---- POST /boards ----

def test_create_board_returns_201(client):
    r = create_board(client)
    assert r.status_code == 201
    data = r.json()
    assert UUID_RE.match(data["id"])
    assert data["name"] is None
    assert data["elements"] == []
    assert DT_RE.match(data["created_at"])


def test_create_board_with_name(client):
    r = create_board(client, "Rate limiter design")
    assert r.status_code == 201
    assert r.json()["name"] == "Rate limiter design"


def test_create_board_without_body(client):
    r = client.post("/boards")
    assert r.status_code == 201
    assert UUID_RE.match(r.json()["id"])


# ---- GET /boards/{board_id} ----

def test_get_board_empty(client):
    board_id = create_board(client).json()["id"]
    r = client.get(f"/boards/{board_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == board_id
    assert data["elements"] == []


def test_get_board_404(client):
    r = client.get(f"/boards/{MISSING_UUID}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Board not found"


def test_get_board_invalid_uuid_422(client):
    r = client.get("/boards/not-a-uuid")
    assert r.status_code == 422


# ---- POST /boards/{board_id}/elements ----

def test_add_sticky_note(client):
    board_id = create_board(client).json()["id"]
    r = add_element(
        client,
        board_id,
        type="sticky_note",
        x=120,
        y=80,
        width=160,
        height=160,
        text="API Gateway",
    )
    assert r.status_code == 201
    data = r.json()
    assert UUID_RE.match(data["id"])
    assert data["board_id"] == board_id
    assert data["type"] == "sticky_note"
    assert data["x"] == 120
    assert data["y"] == 80
    assert data["width"] == 160
    assert data["height"] == 160
    assert data["text"] == "API Gateway"
    assert DT_RE.match(data["created_at"])


def test_add_element_without_text_is_null(client):
    board_id = create_board(client).json()["id"]
    r = add_element(client, board_id, type="rectangle", x=10, y=20, width=180, height=110)
    assert r.status_code == 201
    assert r.json()["text"] is None


def test_add_all_element_types(client):
    board_id = create_board(client).json()["id"]
    for t in ("sticky_note", "rectangle", "circle"):
        r = add_element(client, board_id, type=t, width=100, height=100)
        assert r.status_code == 201
        assert r.json()["type"] == t


def test_add_element_invalid_type_422(client):
    board_id = create_board(client).json()["id"]
    r = add_element(client, board_id, type="triangle")
    assert r.status_code == 422


def test_add_element_missing_field_422(client):
    board_id = create_board(client).json()["id"]
    r = client.post(
        f"/boards/{board_id}/elements",
        json={"type": "circle", "x": 0, "y": 0, "width": 10},
    )
    assert r.status_code == 422


def test_add_element_non_positive_size_422(client):
    board_id = create_board(client).json()["id"]
    r = add_element(client, board_id, width=0)
    assert r.status_code == 422


def test_add_element_to_missing_board_404(client):
    r = add_element(client, MISSING_UUID)
    assert r.status_code == 404
    assert r.json()["detail"] == "Board not found"


def test_add_element_invalid_board_uuid_422(client):
    r = client.post(
        "/boards/not-a-uuid/elements",
        json={"type": "circle", "x": 0, "y": 0, "width": 10, "height": 10},
    )
    assert r.status_code == 422


def test_get_board_lists_elements(client):
    board_id = create_board(client).json()["id"]
    add_element(client, board_id, type="sticky_note", text="a")
    add_element(client, board_id, type="circle")
    data = client.get(f"/boards/{board_id}").json()
    assert len(data["elements"]) == 2
    assert {e["type"] for e in data["elements"]} == {"sticky_note", "circle"}


# ---- DELETE /elements/{element_id} ----

def test_delete_element_204(client):
    board_id = create_board(client).json()["id"]
    element_id = add_element(client, board_id).json()["id"]
    r = client.delete(f"/elements/{element_id}")
    assert r.status_code == 204
    assert r.content == b""


def test_delete_element_removed_from_board(client):
    board_id = create_board(client).json()["id"]
    element_id = add_element(client, board_id).json()["id"]
    assert client.delete(f"/elements/{element_id}").status_code == 204
    assert client.get(f"/boards/{board_id}").json()["elements"] == []


def test_delete_element_404(client):
    r = client.delete(f"/elements/{MISSING_UUID}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Element not found"


def test_delete_element_twice_404(client):
    board_id = create_board(client).json()["id"]
    element_id = add_element(client, board_id).json()["id"]
    assert client.delete(f"/elements/{element_id}").status_code == 204
    assert client.delete(f"/elements/{element_id}").status_code == 404


def test_delete_element_invalid_uuid_422(client):
    r = client.delete("/elements/not-a-uuid")
    assert r.status_code == 422


# ---- GET /healthz ----

def test_healthz_ok(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


# ---- static frontend ----

def test_frontend_served_with_no_cache(client):
    """Static assets must force revalidation, or browsers cache stale JS."""
    for path in ("/", "/app.js", "/style.css"):
        r = client.get(path)
        assert r.status_code == 200, f"{path} should be served"
        assert r.headers.get("cache-control") == "no-cache", f"{path} should be no-cache"
    assert "text/html" in client.get("/").headers["content-type"]
