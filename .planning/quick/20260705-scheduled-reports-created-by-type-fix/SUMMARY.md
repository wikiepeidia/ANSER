---
title: Fix scheduled_reports.created_by column type drift
date: 2026-07-05
slug: scheduled-reports-created-by-type-fix
status: complete
---

# Summary: Fix scheduled_reports.created_by column type drift

## What was done

Live verification (curl, authenticated session, every GET endpoint)
after Phase 33 found two 500s caused by a Postgres type mismatch:
`scheduled_reports.created_by` was `text` while the ownership filter
added in Phase 30 compares it to an integer `user_id`. Confirmed via
`information_schema.columns` that every sibling table's `created_by` is
`bigint`/`integer` — only `scheduled_reports` had drifted. Confirmed the
4 existing rows were all clean numeric strings, then applied:

```sql
ALTER TABLE scheduled_reports
  ALTER COLUMN created_by TYPE BIGINT USING created_by::bigint;
```

on the live database.

## Files touched

- No application code changed — this was a data-layer fix on an
  already-provisioned Postgres database. `core/db/connection.py`'s
  `CREATE TABLE IF NOT EXISTS` already specifies `created_by INTEGER`
  for any fresh install; that statement was simply a no-op against the
  pre-existing table.
- `.planning/quick/20260705-scheduled-reports-created-by-type-fix/PLAN.md`
- `.planning/quick/20260705-scheduled-reports-created-by-type-fix/SUMMARY.md`
- `.planning/STATE.md` — Quick Tasks Completed entry added.

## If you hit the same 500 on another environment

Run the sanity check, then the fix, against that environment's
Postgres:

```sql
SELECT COUNT(*) FROM scheduled_reports
WHERE created_by IS NOT NULL AND created_by !~ '^[0-9]+$';
-- must be 0

ALTER TABLE scheduled_reports
  ALTER COLUMN created_by TYPE BIGINT USING created_by::bigint;
```

## Verification

- `information_schema.columns`: `scheduled_reports.created_by` is now
  `bigint`.
- `curl` (authenticated session): `/api/reports/scheduled` and
  `/api/reports/stats` both return `200` with valid JSON (previously
  `500`).
- Full pytest suite re-run: 178/178 passing, no regression.

## Commit

Documented alongside `.planning/STATE.md` update — see git log for this
quick task's slug.
