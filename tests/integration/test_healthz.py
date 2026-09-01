"""Health endpoint against the real database."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import get_db
from backend.main import app

pytestmark = pytest.mark.integration


def test_healthz_ok(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_healthz_503_when_database_down(client):
    """A session bound to a nonexistent database must surface as 503."""
    bad_engine = create_engine(
        "postgresql+psycopg://canvas:canvas@localhost:5432/nonexistent_db"
    )
    BadSession = sessionmaker(bind=bad_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = BadSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        r = TestClient(app).get("/healthz")
    finally:
        app.dependency_overrides.clear()
        bad_engine.dispose()

    assert r.status_code == 503
    assert r.json()["detail"] == "Database unavailable"
