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

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

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
