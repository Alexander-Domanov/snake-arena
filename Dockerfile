# Syntax: docker build -t interview-canvas:latest .
#
# Single container for the whole app (no Node stage — the frontend is vanilla
# HTML/CSS/JS with no build step; FastAPI serves the static files).
# Dependencies are installed with uv from the lockfile for reproducibility.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# uv — fast, lockfile-driven dependency installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (layer caching: app code changes don't reinstall)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Application code
COPY backend/ backend/
COPY frontend/ frontend/
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic/

# Entrypoint: run migrations, then exec the server command
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Non-root user; /data is where a SQLite volume can be mounted (owned here so
# a fresh named volume inherits write access)
RUN useradd --create-home appuser \
    && mkdir -p /data \
    && chown appuser /data
USER appuser

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD [".venv/bin/uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
