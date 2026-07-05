---
phase: 32-error-handling-data-access-cleanup
plan: "01"
requirements-completed:
  - SEC-04
  - PLAT-01
  - PLAT-02
completed: 2026-07-05
---

# Phase 32 Plan 01: Error Handling & Data Access Cleanup Summary

## Accomplishments

- Added correlation-ID based `safe_api_error()` responses.
- Updated global API exception handling to avoid returning `str(error)` for API 500s.
- Updated sales and AI route exception paths to avoid raw exception disclosure.
- Replaced `routes/sales_routes.py` module-level `db_manager` usage.
- Moved Google OAuth user lookup/update/create/workspace SQL into repository methods.
- Preserved legacy/test behavior for non-API HTTP exceptions and CSRF parity.

## Files Modified

- `app.py`
- `core/security.py`
- `routes/sales_routes.py`
- `routes/ai_routes.py`
- `routes/google_routes.py`
- `core/db/user_repo.py`
- `core/db/connection.py`

