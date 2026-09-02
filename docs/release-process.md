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
   ├─ staging: deploy hook → Render build → migrate → start → /healthz smoke
   ├─ production: only if staging passed → deploy hook → smoke
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

## Deploy: merge to main is the release action

- Merging to `main` triggers the Deploy workflow — this is the single release
  action; there is no separate manual "deploy to production" button in the
  happy path.
- **Staging first, then production.** The workflow POSTs to the staging deploy
  hook, waits for staging `/healthz` to return ok, and only then POSTs to the
  production deploy hook. If staging fails, the guard step aborts production
  promotion — a broken commit never reaches users automatically.
- Render builds the image from the repository at that commit, runs
  `alembic upgrade head` in the entrypoint, starts the server, and Render's own
  health check on `/healthz` confirms the app can reach Postgres.

## Manual deploy / re-run

From GitHub: **Actions → Deploy → Run workflow**, choose `staging` or
`production`. This is useful to re-run a deploy without a code change or to
deploy an environment independently.

## Rollback

Rollback is done in the Render dashboard, not by reverting the commit:

1. Open the service/environment (staging or production).
2. **Deploy → previous successful deploy** (Render keeps a history).
3. Render rebuilds/restarts that image; the database is migrated forward only,
   so rollback does not undo schema changes — check migrations before rolling
   back across a schema change.

The equivalent for CI is `git revert` + PR + merge, which runs the full
pipeline again.

## Rules of thumb

- Small PRs, meaningful commits (see AGENTS.md: commit after each meaningful
  step).
- All API changes land in `openapi.yaml` first; CI and tests keep backend and
  contract in sync.
- Never push to `main` directly for a feature — always through a PR with a
  green CI run. The Deploy workflow fires on push to main by design.
