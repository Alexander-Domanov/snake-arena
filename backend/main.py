"""FastAPI application entrypoint.

Run from the repo root:
    uv run uvicorn backend.main:app --reload

The app serves both the API and the static frontend (single origin),
so the same container/image works in dev and production.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routes import router

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP: create tables on startup (no migrations yet)
    Base.metadata.create_all(bind=engine)
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
