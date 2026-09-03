# Deployment

Interview Canvas is deployed on Render as a Docker web service with a managed
Postgres database. There are two environments: **staging** (development —
deploys automatically on every merge to `main`) and **production** (public —
deploys only through a manual promotion). Deploys are triggered from GitHub
Actions via Render deploy hooks: merge to `main` → build on Render → migrate →
start → smoke test on staging; production is promoted by hand from
**Actions → Deploy → Run workflow → production**.

## Architecture

```text
GitHub (source of truth)
  └─ .github/workflows/deploy.yml
       ├─ push to main ──────────────────────────►  Render staging environment
       │      (development, automatic)              builds image from Dockerfile,
       │                                             runs migrations (entrypoint),
       │                                             starts on :8000, /healthz
       └─ workflow_dispatch (manual, human choice) ─►  Render production environment
              └─ guard: staging /healthz must be ok    (public; promotion only)
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

| Environment | Role | Deploys | Public URL |
|-------------|------|---------|-----------|
| Production  | what users see | manually promoted (workflow_dispatch) | https://interview-canvas.onrender.com |
| Staging     | development: pre-prod validation | automatically on every merge to `main` | https://interview-canvas-staging.onrender.com |

> Staging is the development environment: every merged commit lands there and
> is smoke-tested. Production is updated only by a manual promotion of a
> release that has already been verified on staging (Module 4 dev/prod model:
> push → dev, promote → prod).

## Deploy flow

1. Merge to `main` → `deploy-staging` job POSTs to `RENDER_STAGING_HOOK_URL`
   and polls `<STAGING_URL>/healthz` until it returns ok (up to 5 minutes).
   Every push to `main` reaches staging — this is the development environment.
2. Production is **not** deployed automatically. To promote, a human runs
   **Actions → Deploy → Run workflow** and chooses `production`.
3. `deploy-production` first runs a guard: staging `/healthz` must be ok
   (i.e. the release was actually verified on development). If staging is
   unhealthy, promotion is refused.
4. The guard passes → POST to `RENDER_PRODUCTION_HOOK_URL` → poll
   `<PRODUCTION_URL>/healthz`.

Both environments deploy the current `main` HEAD at trigger time: staging
right after the merge, production whenever the human promotes. Promote soon
after staging is verified — a later merge would change the HEAD that the
promotion deploys.

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
