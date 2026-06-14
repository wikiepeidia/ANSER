---
phase: 25-circular-import-module-decoupling
plan: "01"
subsystem: core
tags:
  - circular-import
  - module-decoupling
  - wsgi
  - dl-client
dependency_graph:
  requires: []
  provides:
    - app.py importable without side effects
    - wsgi.py gunicorn entry point
    - core/services/dl_client.py HTTP-first with no path pollution
  affects:
    - all modules that import from app
    - routes that use DLClient
    - deployment via gunicorn
tech_stack:
  added: []
  patterns:
    - Application factory pattern (create_app guarded under __main__)
    - WSGI entry point convention (application = create_app())
    - HTTP-first client default (use_local=False)
key_files:
  created:
    - wsgi.py
  modified:
    - app.py
    - core/services/dl_client.py
decisions:
  - "Remove module-level app = create_app() from app.py to prevent server startup on import"
  - "Create wsgi.py exporting application for gunicorn compatibility"
  - "Change DLClient use_local default to False so HTTP mode is the safe default in all environments"
  - "Remove unused import sys along with sys.path block since sys had no other references in dl_client.py"
metrics:
  duration: "~10 minutes"
  completed: "2026-06-14"
  tasks_completed: 3
  files_modified: 3
---

# Phase 25 Plan 01: Circular Import & Module Decoupling Summary

**One-liner:** Removed module-level server startup from app.py, created wsgi.py for gunicorn, and stripped sys.path mutation + HTTP-first default from DLClient.

## What Changed

### Task 1: dl_client.py — sys.path block removed, use_local default flipped (CIRC-03, NFR-TD-01)

**Commit:** 934baff

`core/services/dl_client.py` previously ran a `sys.path.insert(0, dl_service_path)` at module level every time any code imported DLClient. This silently mutated the interpreter's module search path. The block (lines 6-10 including comment, `current_dir`, `dl_service_path`, and the `if` guard) was removed entirely. `import sys` was also removed since it was only referenced in that deleted block.

The `__init__` signature default was changed from `use_local=True` to `use_local=False`. All three `if self.use_local:` method bodies (detect_invoice, forecast_quantity, run_ocr) with their lazy imports were left completely untouched — they are the correct pattern.

### Task 2: app.py — module-level instantiation removed; wsgi.py created (CIRC-01, CIRC-02)

**Commit:** c6c999c

`app.py` had a three-line block at lines 240-243 (`# Module-level app instance` comment header + `app = create_app()`) that executed at import time. This caused the Flask server to start spinning up whenever any other module did `import app`. The entire comment block and assignment were deleted.

`app = create_app()` was moved inside `if __name__ == '__main__':` as the first statement, before the `db_manager.init_database()` call. The `run_dl_service` function definition between `create_app` and the `__main__` block was left in place — it is not affected.

`wsgi.py` was created at the project root with the minimal required content:

```python
from app import create_app

application = create_app()
```

The exported name is `application` (not `app`) so gunicorn can serve via `gunicorn wsgi:application` without extra config.

### Task 3: End-to-end verification (NFR-TD-01, NFR-TD-02)

All four final verification checks passed:

| Check | Command | Result |
|-------|---------|--------|
| NFR-TD-01 | `grep -rn "sys.path" core/` | No matches — PASS |
| CIRC-01 | `python -c "import app"` | Exit 0, no output — PASS |
| CIRC-02 | `python -c "from wsgi import application; print(type(application))"` | `<class 'flask.app.Flask'>` — PASS |
| CIRC-03 | `python -c "from core.services.dl_client import DLClient; c = DLClient(); assert not c.use_local; print('HTTP default OK')"` | `HTTP default OK` — PASS |

## Deviations from Plan

None — plan executed exactly as written. The only judgment call was confirming `sys` had no other references in `dl_client.py` before removing `import sys`; the full file scan confirmed it was only used in the deleted block.

## Known Stubs

None. No placeholder text or hardcoded empty values introduced.

## Threat Flags

No new security surface introduced beyond what the threat model identified:
- `wsgi.py` is an infrastructure file at project root — no new trust boundary.
- `DLClient` now defaults to `DL_SERVICE_URL` (env var, defaults to `localhost:5001`) — no credentials sent, low-value in local dev context.

## Self-Check

| Item | Status |
|------|--------|
| wsgi.py exists at project root | FOUND |
| app.py has no module-level `app = create_app()` | CONFIRMED (grep returns no match on `^app = create_app`) |
| core/services/dl_client.py has no sys.path code | CONFIRMED |
| Commit 934baff exists | VERIFIED |
| Commit c6c999c exists | VERIFIED |

## Self-Check: PASSED
