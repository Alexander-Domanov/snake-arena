# Deployment

Interview Canvas is deployed on Render as a Docker web service with a managed
Postgres database. There are two environments: **staging** (validation) and
**production** (public). Deploys are triggered from GitHub Actions via Render
deploy hooks, so the pipeline is: merge to `main` → build on Render →
migrate → start → smoke test → same for the other environment.

## Architecture

```text
GitHub (source of truth)
  └─ .github/workflows/deploy.yml        (triggered on push to main)
       ├─ POST staging deploy hook  ──►  Render staging environment
       │                                   builds image from Dockerfile,
       │                                   runs migrations (entrypoint),
       │                                   starts on :8000, /healthz
       └─ POST production deploy hook ──►  Render production environment
```

- **Infrastructure as code**: `render.yaml` (Render Blueprint) provisions the
  web service and the managed Postgres instance.
- **Container**: one multi-stage image from `Dockerfile` (uv stage + runtime
  stage) — Python 3.11, dependencies installed with `uv` from the lockfile.
  The frontend is static files served by FastAPI, so no Node stage is needed.
- **Migrations**: `docker-entrypoint.sh` runs `alembic upgrade head` before
  the server starts, so every deploy migrates the database automatically.
- **Database**: managed Postgres on Render. Render injects `DATABASE_URL` as a
  plain `postgresql://` URL; the app normalizes it to the `psycopg` driver at
  startup. Locally (dev, tests) the same variable points to SQLite or to the
  docker-compose Postgres.

## Environments

| Environment | Purpose | Public URL |
|-------------|---------|-----------|
| Production  | what users see | https://interview-canvas.onrender.com |
| Staging     | pre-prod validation of the same image | https://interview-canvas-staging.onrender.com |

> Both environments run the same image built from the same commit; staging is
> deployed first and must pass its health check before production is deployed.

## Deploy flow

1. Push to `main` (or run the workflow manually via
   **Actions → Deploy → Run workflow**, choosing staging or production).
2. `deploy-staging` job POSTs to `RENDER_STAGING_HOOK_URL`, then polls
   `<STAGING_URL>/healthz` until it returns `{"ok": ...}` (up to 5 minutes).
3. `deploy-production` job runs only if staging succeeded (guard step), POSTs
   to `RENDER_PRODUCTION_HOOK_URL`, then polls `<PRODUCTION_URL>/healthz`.
4. A failed staging deploy blocks production promotion.

## Health check

Render also uses `/healthz` for its own instance health (defined in
`render.yaml` via `healthCheckPath`). It returns HTTP 200 only when the app is
up **and** the database is reachable — so a green deploy implies the database
migrations ran and the app can talk to Postgres.

## Required GitHub secrets

| Secret | Value |
|--------|-------|
| `RENDER_STAGING_HOOK_URL` | Deploy hook for the staging environment (Render dashboard → service/environment → Settings → Deploy Hooks) |
| `RENDER_PRODUCTION_HOOK_URL` | Deploy hook for the production environment |
| `STAGING_URL` | Public staging URL: https://interview-canvas-staging.onrender.com |
| `PRODUCTION_URL` | Public production URL: https://interview-canvas.onrender.com |

Deploy hooks contain the auth key in the URL itself — they are secrets, never
commit them. The workflow only POSTs to them.

## Manual verification

```bash
# Trigger a Render deploy directly (same as the workflow does)
curl -fsS -X POST "https://api.render.com/deploy/srv-XXXX?key=YYYY"

# Health check against a live environment
curl -fsS https://interview-canvas-staging.onrender.com/healthz
curl -fsS https://interview-canvas.onrender.com/healthz
```

## Costs

Free-tier Render instance and free managed Postgres. Free instances spin down
after inactivity; the first request after idle takes a few extra seconds to
wake the instance (this is expected and is not an outage).
