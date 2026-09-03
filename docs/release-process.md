# Release Process

How a change goes from a local commit to the public production URL.

## Pipeline at a glance

```text
feature branch
   │  push → open PR
   ▼
GitHub Actions CI (every pull request)
   ├─ backend unit tests
   ├─ frontend tests
   ├─ integration tests (real Postgres)
   ├─ e2e tests (docker compose + Playwright)
   └─ Docker image build
   │
   │  all green
   ▼
merge to main
   ▼
GitHub Actions Deploy (push to main)
   ├─ build-and-push: docker build → ghcr.io/alexander-domanov/snake-arena:<YYYYMMDD-HHMMSS-sha>
   └─ deploy-staging (development): Render hook + imgURL=<that tag> → /healthz smoke
   │
   │  human verifies staging (and notes the image tag from the run)
   ▼
manual promotion (Actions → Deploy → workflow_dispatch → production + image tag)
   └─ guard: tag format ok, staging /healthz ok → Render hook + imgURL=<same tag> → smoke
   ▼
live
```

## CI gate: merge only on green

- CI (`ci.yml`) runs on **every pull request**: lint (ruff), unit, frontend,
  integration against real Postgres, E2E against the full docker-compose stack,
  and a Docker image build.
- A PR with failing checks should not be merged. CI needs no secrets and uses
  only ephemeral services, so the result is reproducible locally too.
- GitHub branch protection is **enabled on `main`**: direct pushes are
  blocked, a PR is required, and all six CI checks (Lint, Backend unit tests,
  Frontend tests, Integration tests, E2E tests, Docker image build) must pass
  before merge. A PR with failing checks cannot be merged.

## Deploy: one build, one image, two environments

- Merging to `main` triggers the Deploy workflow:
  1. **build-and-push** builds the image and pushes it to GHCR with tags
     `YYYYMMDD-HHMMSS-<shortsha>` and `:latest`. A failed build stops the run —
     nothing deploys.
  2. **deploy-staging** deploys that exact tag to the development environment
     (Render deploy hook + `imgURL`), then waits for `/healthz`.
- **Production is never deployed automatically.** It is promoted by a human:
  **Actions → Deploy → Run workflow**, choose `production`, and paste the image
  tag that was verified on staging. The promotion deploys the **same image
  bytes** that ran on staging (no rebuild, no drift).
- The promotion job guards twice: the tag must match the
  `YYYYMMDD-HHMMSS-shortsha` format, and staging `/healthz` must be ok. A
  broken or unverified release never reaches users.
- Render pulls the image and runs `alembic upgrade head` in the entrypoint
  before starting; Render's own health check on `/healthz` confirms the app
  can reach Postgres.

## Manual deploy / re-run

From GitHub: **Actions → Deploy → Run workflow**.

- `staging` — rebuilds from the current `main` HEAD and deploys staging
  (same as the push path, useful to re-run a deploy without a code change).
- `production` — the manual promotion: fill in the image tag from the last
  successful staging deploy, staging must be healthy (guard), then production
  is deployed and smoke-tested.

## Rollback

Rollback is done in the Render dashboard, not by reverting the commit:

1. Open the service (staging or production).
2. **Deploy → previous successful deploy** (Render keeps a history).
3. Render re-pulls that deploy's image from GHCR, so the image must still
   exist in the registry — keep old tags, prune them only when old enough that
   rollback to them is no longer plausible.
4. The database is migrated forward only, so rollback does not undo schema
   changes — check migrations before rolling back across a schema change.

The equivalent for CI is `git revert` + PR + merge, which runs the full
pipeline again (build → staging; production still needs a manual promotion).

## Rules of thumb

- Small PRs, meaningful commits (see AGENTS.md: commit after each meaningful
  step).
- All API changes land in `openapi.yaml` first; CI and tests keep backend and
  contract in sync.
- Never push to `main` directly for a feature — always through a PR with a
  green CI run. The Deploy workflow fires on push to main by design (staging
  only); production changes need the manual promotion on top.
- The deployable artifact is the tagged image, not the commit: what you verify
  on staging is exactly what you promote to production.
