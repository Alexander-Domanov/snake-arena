---
name: review-api-change
description: Review an API change against the OpenAPI contract and test suite; report PASS or FAIL with file:line evidence. Never edit code.
---

# Review an API change

Use this skill to review a proposed API change (a branch, a PR, or an
uncommitted diff) from a QA perspective. Your output is a verdict, not a
patch: **never modify code or files**. The implementer receives your findings
and decides on the fix.

## Inputs

- The change to review: `git diff main...HEAD`, or a PR number/URL.
- Repo ground truth: `openapi.yaml` (source of truth), `AGENTS.md`
  (rules/conventions), `product-spec.md` (requirements).

## What to check

1. **Contract-first ordering and sync.** If `backend/` changed, did
   `openapi.yaml` change too (in the same change)? Do the pydantic schemas in
   `backend/schemas.py` match the OpenAPI schemas field-for-field (names,
   types, bounds, required/optional)? Does `backend/routes.py` implement
   exactly the declared paths/methods?
2. **Status codes and errors.** Create → 201, delete → 204, read/update →
   200; missing resource → 404, invalid payload → 422. Are uuid path
   parameters annotated `uuid.UUID` (garbage → 422)? Are datetimes serialized
   RFC3339 UTC with `Z`?
3. **Data integrity.** Cascade delete on the ORM relationship; `selectinload`
   where a response serializes a relationship; no N+1 regressions on board
   reads; `exclude_unset` semantics preserved for partial updates.
4. **Tests.** Are there tests at the right layers (unit/API against in-memory
   SQLite, integration against Postgres for persistence/migrations)? Do they
   cover the new status codes and the failure paths? Do they actually run —
   check the collection hook does not silently skip (repo lesson: a green CI
   that skipped everything is not green)? Run them if feasible:
   ```bash
   uv run pytest -m "not integration" -q
   ```
5. **Frontend contract usage.** If the UI changed: no hardcoded URLs; payload
   keys match the contract (`sticky_note`, `rectangle`, `circle`); reload the
   board after mutations; error handling distinguishes 404 (quiet) from
   server-down (visible banner).

## Output format

```
VERDICT: PASS|FAIL

Findings (each with file:line evidence):
1. [SEV: high/med/low] description — path:line
2. ...

If FAIL: the single most important fix, stated as one imperative sentence.
If PASS: one line on what was verified.
```

Do not expand scope: review only what the change touches.
