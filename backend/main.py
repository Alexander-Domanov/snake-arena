"""FastAPI application entrypoint.

Run from the repo root:
    uv run uvicorn backend.main:app --reload

The app serves both the API and the static frontend (single origin),
so the same container/image works in dev and production.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from alembic import command

from .routes import router

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migrations run on startup (idempotent): a fresh DB gets the schema here,
    # and production runs the same command as part of the deploy.
    command.upgrade(Config(str(ALEMBIC_INI)), "head")
    yield


app = FastAPI(
    title="Interview Canvas API",
    description="REST API for Interview Canvas. Contract: openapi.yaml (OpenAPI 3.0).",
    version="0.1.0",
    lifespan=lifespan,
)

# Frontend (file:// or dev server) and the API are on different origins during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Serve the static frontend from the same origin (production pattern).
# Mounted last so API routes (/boards, /elements, /healthz) take precedence.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
