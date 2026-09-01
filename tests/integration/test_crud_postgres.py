"""Full CRUD lifecycle against a real Postgres database."""
import re

import pytest

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MISSING_UUID = "00000000-0000-0000-0000-000000000000"

pytestmark = pytest.mark.integration


def create_board(client, name=None):
    body = {"name": name} if name is not None else {}
    return client.post("/boards", json=body)


def add_element(client, board_id, **overrides):
    payload = {"type": "circle", "x": 0, "y": 0, "width": 130, "height": 130}
    payload.update(overrides)
    return client.post(f"/boards/{board_id}/elements", json=payload)


def test_full_lifecycle_on_postgres(client):
    # create board
    r = create_board(client, "integration")
    assert r.status_code == 201
    board = r.json()
    assert UUID_RE.match(board["id"])
    bid = board["id"]

    # add all element types
    sticky = add_element(
        client, bid, type="sticky_note", x=10, y=20, width=160, height=160, text="hello pg"
    )
    assert sticky.status_code == 201
    rect = add_element(client, bid, type="rectangle", x=30, y=40, width=180, height=110)
    circle = add_element(client, bid, type="circle", x=50, y=60, width=130, height=130)
    assert {r.status_code for r in (rect, circle)} == {201}

    # the board lists all elements, in the order they were added
    data = client.get(f"/boards/{bid}").json()
    assert [e["type"] for e in data["elements"]] == ["sticky_note", "rectangle", "circle"]
    assert data["elements"][0]["text"] == "hello pg"
    assert all(UUID_RE.match(e["id"]) for e in data["elements"])

    # delete one element
    assert client.delete(f"/elements/{sticky.json()['id']}").status_code == 204
    data = client.get(f"/boards/{bid}").json()
    assert [e["type"] for e in data["elements"]] == ["rectangle", "circle"]

    # 404s
    assert client.get(f"/boards/{MISSING_UUID}").status_code == 404
    assert client.delete(f"/elements/{MISSING_UUID}").status_code == 404
    assert add_element(client, MISSING_UUID).status_code == 404


def test_data_persists_across_sessions(client):
    """What one participant writes, another session (fresh client) can read."""
    from fastapi.testclient import TestClient

    from backend.main import app

    bid = create_board(client).json()["id"]
    add_element(client, bid, type="sticky_note", x=5, y=5, width=160, height=160, text="shared")

    # a brand-new client instance on the same database sees the data
    # (the dependency override installed by the client fixture is still active)
    second = TestClient(app)
    data = second.get(f"/boards/{bid}").json()
    assert len(data["elements"]) == 1
    assert data["elements"][0]["text"] == "shared"


def test_create_boards_are_unique(client):
    ids = {create_board(client).json()["id"] for _ in range(5)}
    assert len(ids) == 5
