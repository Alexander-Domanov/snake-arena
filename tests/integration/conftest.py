"""Integration test setup: real Postgres, schema from Alembic migrations.

These tests use a dedicated database (canvas_test by default) so they never
touch the dev database. The schema comes from `alembic upgrade head` — the
same path production uses.

Requires Postgres on the host port. Start it with:
    docker compose up -d

When Postgres is unreachable, every test in this directory is skipped with a
hint (so a plain `uv run pytest` still works on a machine without Docker).
"""
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from backend.database import get_db
from backend.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"

ADMIN_URL = os.getenv(
    "TEST_DATABASE_ADMIN_URL",
    "postgresql+psycopg://canvas:canvas@localhost:5432/canvas",
)
TEST_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://canvas:canvas@localhost:5432/canvas_test",
)


def _postgres_reachable() -> bool:
    try:
        engine = create_engine(ADMIN_URL, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    """Skip the whole integration suite when Postgres is unreachable.

    Done at collection time (not via a fixture) so the skip reliably wins
    over any fixture setup that needs the database.
    """
    if not _postgres_reachable():
        skip = pytest.mark.skip(reason="Postgres unavailable — start it with: docker compose up -d")
        for item in items:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def test_db():
    """Fresh dedicated test database, schema applied via Alembic."""
    db_name = make_url(TEST_URL).database

    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT", poolclass=NullPool)
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin.dispose()

    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    command.upgrade(cfg, "head")

    engine = create_engine(TEST_URL, poolclass=NullPool)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield Session
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_db(test_db):
    """Start every test from empty tables (isolated but fast)."""
    Session = test_db
    db = Session()
    try:
        db.execute(text("TRUNCATE boards, elements RESTART IDENTITY CASCADE"))
        db.commit()
    finally:
        db.close()
    yield


@pytest.fixture()
def client(test_db):
    """TestClient wired to the real Postgres test database."""
    Session = test_db

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
