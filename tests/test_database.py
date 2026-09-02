"""Unit tests for the database configuration (database-agnostic setup)."""
from backend.database import (
    DATABASE_URL,
    DB_PATH,
    PROJECT_ROOT,
    engine,
    normalize_database_url,
)


def test_default_database_is_sqlite_file_in_repo_root():
    assert PROJECT_ROOT.name == "snake-arena"
    assert DB_PATH == PROJECT_ROOT / "db.sqlite3"
    assert engine.url.drivername == "sqlite"
    assert engine.url.database == str(DB_PATH)


def test_database_url_default_matches_sqlite_path():
    # without DATABASE_URL in the environment, the engine points at the repo-root file
    assert DATABASE_URL == f"sqlite:///{DB_PATH}"


def test_normalize_database_url_routes_postgres_to_psycopg():
    # managed providers hand out plain postgresql:// URLs; we only install psycopg v3
    assert (
        normalize_database_url("postgresql://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )
    # sqlite and already-qualified URLs are left untouched
    assert normalize_database_url("sqlite:////data/app.db") == "sqlite:////data/app.db"
    assert (
        normalize_database_url("postgresql+psycopg://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )
