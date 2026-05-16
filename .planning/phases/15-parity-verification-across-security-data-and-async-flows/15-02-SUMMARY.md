---
phase: 15-parity-verification-across-security-data-and-async-flows
plan: 02
subsystem: parity-data-async
tags:
  - parity
  - data
  - postgres
  - sqlite
  - async
requires:
  - 15-01
provides:
  - sqlite/postgresql-shim write-path parity tests
  - async lifecycle state parity tests (pending/processing/completed/failed)
affects:
  - tests/parity/test_data_async_parity.py
tech-stack:
  added: []
  patterns:
    - db mode parity via shim-aware fakes
    - async lifecycle parity via deterministic monkeypatching
key-files:
  created:
    - tests/parity/test_data_async_parity.py
requirements-completed:
  - DATA-01
  - DATA-02
duration: 15 min
completed: 2026-04-16
---

# Phase 15 Plan 02: Data and async parity

Implemented and executed deterministic parity tests validating critical DB write behavior in SQLite/PostgreSQL-shim paths and async AI job lifecycle state transitions.

## Execution Summary

- Start Time: 2026-04-16T05:17:00Z
- End Time: 2026-04-16T05:32:00Z
- Tasks Completed: 3/3

## Task Outcomes

### Task 1: DB write-path parity

- Added SQLite-mode write parity test for workflow create path.
- Added PostgreSQL-shim parity test asserting placeholder translation and committed writes.

Verification:

- `python -m pytest tests/parity/test_data_async_parity.py::test_db_write_parity_sqlite_mode tests/parity/test_data_async_parity.py::test_db_write_parity_postgres_shim_mode -q`

### Task 2: Async lifecycle parity

- Added pending+processing lifecycle parity test for `create_chat_job`.
- Added completed lifecycle parity test for `background_ai_task` success path.
- Added failed lifecycle parity test for `background_ai_task` failure path.

Verification:

- `python -m pytest tests/parity/test_data_async_parity.py::test_async_job_pending_and_processing_parity tests/parity/test_data_async_parity.py::test_background_ai_task_completed_parity tests/parity/test_data_async_parity.py::test_background_ai_task_failed_parity -q`

### Task 3: Full parity suite run

- Ran full data+async parity module successfully.

Verification:

- `python -m pytest tests/parity/test_data_async_parity.py -q`

## Deviations from Plan

None.

## Self-Check

- DATA-01 parity checks pass.
- DATA-02 parity checks pass.
