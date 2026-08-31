"""FastAPI application entrypoint.

Run from the repo root:
    uv run uvicorn backend.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import Base, engine
from .routes import router


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

app.include_router(router)
