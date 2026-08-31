"""Unit tests for the database configuration (database-agnostic setup)."""
from backend.database import DB_PATH, DATABASE_URL, PROJECT_ROOT, engine


def test_default_database_is_sqlite_file_in_repo_root():
    assert PROJECT_ROOT.name == "snake-arena"
    assert DB_PATH == PROJECT_ROOT / "db.sqlite3"
    assert engine.url.drivername == "sqlite"
    assert engine.url.database == str(DB_PATH)


def test_database_url_default_matches_sqlite_path():
    # without DATABASE_URL in the environment, the engine points at the repo-root file
    assert DATABASE_URL == f"sqlite:///{DB_PATH}"
