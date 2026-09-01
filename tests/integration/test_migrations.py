"""Alembic migrations against a real database (the deploy path)."""
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from conftest import ALEMBIC_INI, TEST_URL

pytestmark = pytest.mark.integration


def _alembic_cfg():
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    return cfg


def test_upgrade_head_creates_tables(test_db):
    """The initial migration creates the expected schema on a fresh database."""
    engine = create_engine(TEST_URL)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert {"boards", "elements", "alembic_version"} <= tables


def test_upgrade_is_idempotent(test_db):
    """Running the same migration twice is a no-op."""
    command.upgrade(_alembic_cfg(), "head")  # second run after conftest's upgrade

    # full roundtrip: downgrade to base, then upgrade again
    command.downgrade(_alembic_cfg(), "base")
    command.upgrade(_alembic_cfg(), "head")

    engine = create_engine(TEST_URL)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert {"boards", "elements"} <= tables


def test_migration_matches_models(test_db):
    """The migrated schema is what the ORM models declare (no drift)."""
    from sqlalchemy import MetaData

    from backend.database import Base
    from backend.models import Board, Element  # noqa: F401  (register on metadata)

    engine = create_engine(TEST_URL)
    try:
        insp = inspect(engine)
        db_cols = {
            (t, c["name"])
            for t in insp.get_table_names()
            for c in insp.get_columns(t)
            if t in ("boards", "elements")
        }
    finally:
        engine.dispose()

    model_cols = {
        (t.name, c.name)
        for t in Base.metadata.sorted_tables
        for c in t.columns
        if t.name in ("boards", "elements")
    }
    assert db_cols == model_cols
