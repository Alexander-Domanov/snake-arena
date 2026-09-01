#!/bin/sh
set -e

# Run migrations before serving. Retry while the database is still starting up
# (docker-compose also gates on the db healthcheck; this is belt-and-suspenders
# for direct `docker run` against a just-started Postgres).
n=0
until .venv/bin/alembic upgrade head; do
  n=$((n + 1))
  if [ "$n" -ge 30 ]; then
    echo "Migrations failed after 30 attempts" >&2
    exit 1
  fi
  echo "Database not ready, retrying... ($n/30)" >&2
  sleep 2
done

exec "$@"
