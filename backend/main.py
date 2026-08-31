"""FastAPI application entrypoint.

Run from the repo root:
    uv run uvicorn backend.main:app --reload
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Frontend (file:// or dev server) and the API are on different origins during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
