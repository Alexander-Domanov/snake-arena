"""Database setup.

The app is database-agnostic: the connection string comes from the DATABASE_URL
environment variable and defaults to SQLite (db.sqlite3 in the repo root).
Postgres can be swapped in later by setting, for example:
    DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/interview_canvas
No code changes needed — SQLAlchemy models and services are driver-agnostic.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "db.sqlite3"

_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")


def normalize_database_url(url: str) -> str:
    """Map plain postgresql:// to the installed driver (psycopg v3).

    Managed providers (Render, Railway, Fly) hand out postgresql:// URLs; the
    SQLAlchemy default dialect for that scheme is psycopg2, which we do not
    install. Explicitly route to postgresql+psycopg instead.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = normalize_database_url(_DATABASE_URL)

# FastAPI runs sync endpoints in a threadpool, so SQLite needs the shared
# connection flag. Other drivers don't need (or accept) this argument.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
