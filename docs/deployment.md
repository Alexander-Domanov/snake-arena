# Deployment

Interview Canvas runs on Render as an **image-backed** Docker web service with
a managed Postgres database. The image is built once in CI and pushed to the
GitHub Container Registry (GHCR); Render pulls that exact image — never builds
it. There are two environments: **staging** (development — deploys
automatically on every merge to `main`) and **production** (public — deploys
only through a manual promotion).

## Architecture

```text
GitHub Actions (deploy.yml)
  ├─ build-and-push (push to main or manual staging re-run)
  │    docker build → push to ghcr.io/alexander-domanov/snake-arena
  │    tags: YYYYMMDD-HHMMSS-<shortsha>  +  :latest
  ▼
  ├─ deploy-staging (automatic on push)
  │    Render deploy hook + imgURL=<built tag>  →  staging /healthz smoke
  └─ deploy-production (MANUAL: Actions → Deploy → workflow_dispatch → production)
       guard: staging /healthz ok
       human provides the image tag verified on staging
       Render deploy hook + imgURL=<same tag>  →  production /healthz smoke
```

- **Container registry**: GHCR (public — the repo is public). The image tag
  `YYYYMMDD-HHMMSS-<shortsha>` identifies the exact artifact that runs on
  staging and, after promotion, on production — the same bytes, guaranteed.
- **Container**: one multi-stage image from `Dockerfile` (uv stage + runtime
  stage) — Python 3.11, dependencies installed with `uv` from the lockfile.
  The frontend is static files served by FastAPI, so no Node stage is needed.
  Built for `linux/amd64` (Render requirement).
- **Render services are image-backed**: created in the Render dashboard with
  **Existing Image** pointing at `ghcr.io/alexander-domanov/snake-arena:latest`.
  `render.yaml` (Render Blueprint) remains as the provisioning record for the
  managed Postgres instance; the web services are dashboard-managed after the
  Module 4 registry migration.
- **Registry credential on Render**: a GHCR credential (GitHub PAT with
  `read:packages`) attached to the services (Workspace Settings → Container
  Registry Credentials) so Render can pull the private-by-default image.
- **Migrations**: `docker-entrypoint.sh` runs `alembic upgrade head` before
  the server starts, so every deploy migrates the database automatically.
- **Database**: managed Postgres on Render. Render injects `DATABASE_URL` as a
  plain `postgresql://` URL; the app normalizes it to the `psycopg` driver at
  startup. Locally (dev, tests) the same variable points to SQLite or to the
  docker-compose Postgres.

## Environments

| Environment | Role | Deploys | Public URL |
|-------------|------|---------|-----------|
| Production  | what users see | manually promoted (workflow_dispatch + image tag) | https://interview-canvas.onrender.com |
| Staging     | development: pre-prod validation | automatically on every merge to `main` | https://interview-canvas-staging.onrender.com |

> Staging is the development environment: every merged commit is built,
> pushed to GHCR and deployed there. Production is updated only by a manual
> promotion of the exact image tag that was verified on staging (Module 4
> dev/prod model: push → dev, promote → prod).

## Deploy flow

1. Merge to `main` → `build-and-push` builds the image and pushes
   `ghcr.io/alexander-domanov/snake-arena:<YYYYMMDD-HHMMSS-sha>` and `:latest`.
2. `deploy-staging` (needs the build) POSTs to `RENDER_STAGING_HOOK_URL` with
   `&imgURL=<that exact tag>`, then polls `<STAGING_URL>/healthz` (up to 5
   minutes). Every push reaches the development environment.
3. Production is **not** deployed automatically. To promote, a human opens
   **Actions → Deploy → Run workflow**, chooses `production` and pastes the
   image tag from the last successful staging deploy (shown in that run).
4. `deploy-production` validates the tag format, checks staging `/healthz`
   (guard), then POSTs to `RENDER_PRODUCTION_HOOK_URL` with `&imgURL=<same
   tag>` and polls `<PRODUCTION_URL>/healthz`.
5. A failed build never deploys (step 1 fails the run); an unhealthy staging
   blocks promotion (step 4 guard).

## Health check

Render uses `/healthz` as its instance health check. It returns HTTP 200 only
when the app is up **and** the database is reachable — so a green deploy
implies the database migrations ran and the app can talk to Postgres.

## Required GitHub secrets

| Secret | Value |
|--------|-------|
| `RENDER_STAGING_HOOK_URL` | Deploy hook of the **image-backed** staging service (Render dashboard → service → Settings → Deploy Hook) |
| `RENDER_PRODUCTION_HOOK_URL` | Deploy hook of the **image-backed** production service |
| `STAGING_URL` | Public staging URL: https://interview-canvas-staging.onrender.com |
| `PRODUCTION_URL` | Public production URL: https://interview-canvas.onrender.com |

Deploy hooks contain the auth key in the URL itself — they are secrets, never
commit them. The workflow POSTs to them and appends the URL-encoded
`imgURL` parameter so Render pulls the requested tag instead of the service's
default (`:latest`). All parts of the image reference except the tag must match
the service's configured image, otherwise Render rejects the request (404).

## Manual verification

```bash
# Trigger a Render deploy of a specific tag directly (same as the workflow does)
TAG=20260903-153012-a1b2c3d
IMGURL=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "ghcr.io/alexander-domanov/snake-arena@${TAG}")
curl -fsS -X POST "https://api.render.com/deploy/srv-XXXX?key=YYYY&imgURL=${IMGURL}"

# Health check against a live environment
curl -fsS https://interview-canvas-staging.onrender.com/healthz
curl -fsS https://interview-canvas.onrender.com/healthz
```

## Rollback

Render dashboard → service → **Deploy → previous successful deploy**. For an
image-backed service the rollback re-pulls that deploy's image, so the image
must still exist in GHCR. Old tagged images are therefore kept, not
overwritten; prune them occasionally (they are not needed for rollback once
the deploy is old).

## Costs

Free-tier Render instances and free managed Postgres. GHCR is free for public
repositories (this repo is public). Free instances spin down after inactivity;
the first request after idle takes a few extra seconds to wake the instance
(this is expected and is not an outage).
