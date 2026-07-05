---
title: Fix scheduled_reports.created_by column type drift
date: 2026-07-05
slug: scheduled-reports-created-by-type-fix
status: complete
---

# Quick Task: Fix scheduled_reports.created_by column type drift

## Description

Post-Phase-33 live verification (curl sweep of every authenticated GET
endpoint against the running Postgres-backed app) turned up two 500s:

- `GET /api/reports/scheduled`
- `GET /api/reports/stats`

Both failed with:

```
operator does not exist: text = integer
LINE 1: ...created_by = 3379
```

## Root Cause

Phase 30 added an ownership filter (`_owner_clause()` in
`core/services/operations_service.py`) that compares `created_by` against
an integer `user_id`. Every ownership-scoped table's `created_by` column
is `bigint`/`integer` **except** `scheduled_reports`, which was `text` —
leftover from before that column's type convention was established.
`CREATE TABLE IF NOT EXISTS` in `core/db/connection.py:386` already
declares `created_by INTEGER` for fresh installs, but it's a no-op on a
table that already exists, so the drift persisted silently on any
already-provisioned database.

The full pytest suite (178 tests) never caught this because it runs
against SQLite, which doesn't enforce column types — the mismatch only
surfaces on real Postgres.

## Scope

- Inspect the live Postgres schema for every `created_by` column to
  confirm which table(s) drifted.
- Confirm `scheduled_reports` data is safe to cast (no nulls, no
  non-numeric values).
- Apply the type fix on the live database.
- Re-verify both endpoints return 200 with a real authenticated session.

## Out of Scope

- No code changes required — `connection.py`'s `CREATE TABLE` already
  specifies the correct type for new installs. This was pure data-layer
  drift on an already-existing table.
- Other developers'/environments' own Postgres instances (staging,
  local, other Neon branches) may carry the same drift if their
  `scheduled_reports` table was created before this convention existed.
  See Fix below if you hit the same 500.

## Fix

```sql
ALTER TABLE scheduled_reports
  ALTER COLUMN created_by TYPE BIGINT USING created_by::bigint;
```

Safe to run any time — only fails if the column contains non-numeric
values (verify with the query below first).

```sql
-- Sanity check before running the ALTER on any other environment:
SELECT COUNT(*) FROM scheduled_reports
WHERE created_by IS NOT NULL AND created_by !~ '^[0-9]+$';
-- Must return 0 before the ALTER is safe.
```

## Verification

- `information_schema.columns` confirms `scheduled_reports.created_by`
  is now `bigint` (matches `customers`, `products`,
  `export_transactions`, `import_transactions`, `se_automations`).
- `curl` against a real authenticated session: both
  `/api/reports/scheduled` and `/api/reports/stats` return `200` with
  valid JSON instead of `500`.
- Full pytest suite re-run after the change: still 178/178 passing.
