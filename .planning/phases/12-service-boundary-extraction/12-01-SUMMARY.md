---
phase: 12-service-boundary-extraction
plan: 01
subsystem: backend-services
tags:
  - refactor
  - service-boundary
  - tests
requires: []
provides:
  - core/services/workflow_service.py
  - core/services/ai_chat_service.py
  - core/services/inventory_tx_service.py
  - tests/services/test_extraction_contracts.py
affects:
  - app.py
tech-stack:
  added: []
  patterns:
    - contract-first service modules
    - flask-independent service signatures
key-files:
  created:
    - .planning/phases/12-service-boundary-extraction/12-handler-extraction-map.md
    - core/services/service_errors.py
    - core/services/workflow_service.py
    - core/services/ai_chat_service.py
    - core/services/inventory_tx_service.py
    - tests/services/conftest.py
    - tests/services/test_extraction_contracts.py
  modified: []
key-decisions:
  - "D-04: Service contracts accept plain Python inputs and avoid Flask globals"
  - "D-07: Extraction map maintained as the migration ledger"
requirements-completed:
  - REFAC-06
  - TEST-02
duration: 10 min
completed: 2026-04-16
---

# Phase 12 Plan 01: Extraction map and service contract foundation

Established the handler extraction ledger and created contract-first service modules with a dedicated service test scaffold for Wave 1 baseline.

## Execution Summary

- Start Time: 2026-04-16T03:15:00Z
- End Time: 2026-04-16T03:25:00Z
- Tasks Completed: 2/2
- Files Created: 7
- Task Commits:
  - Task 1: no commit (artifact is gitignored under .planning)
  - Task 2: 34d9df2

## Task Outcomes

### Task 1: Handler extraction map baseline

Created `.planning/phases/12-service-boundary-extraction/12-handler-extraction-map.md` with required columns and seeded high-risk rows for workflow, AI, and import/export handlers. All seeded rows are marked `pending`.

Verification:

- `grep -n "run_workflow\|ai_chat\|api_create_import\|api_create_export\|Delegation Status" .planning/phases/12-service-boundary-extraction/12-handler-extraction-map.md`

### Task 2: Service contracts and service-test scaffold

Created service exception taxonomy and contract modules:

- `core/services/service_errors.py`
- `core/services/workflow_service.py`
- `core/services/ai_chat_service.py`
- `core/services/inventory_tx_service.py`

Created service test scaffold:

- `tests/services/conftest.py`
- `tests/services/test_extraction_contracts.py`

Verification:

- `python -m pytest tests/services/test_extraction_contracts.py -q`

## Deviations from Plan

- [Rule 3 - Blocking] Task 1 commit skipped because the extraction-map artifact is under `.planning/` (gitignored by project settings). Task 2 still produced the required atomic commit for tracked source/test files.

Total deviations: 1 auto-handled (Rule 3)
Impact: low; no functional behavior affected.

## Authentication Gates

None.

## Self-Check: PASSED

- Key files exist on disk.
- At least one `12-01` commit exists: `34d9df2`.
- Contract test suite is green.

## Next Plan Readiness

Ready for Plan 12-02 (workflow and AI delegation). The extraction map and service contracts are in place for route-level delegation work.
