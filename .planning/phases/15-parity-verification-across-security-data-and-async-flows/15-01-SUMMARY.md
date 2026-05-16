---
phase: 15-parity-verification-across-security-data-and-async-flows
plan: 01
subsystem: parity-middleware-contracts
tags:
  - parity
  - contracts
  - security
  - middleware
requires:
  - 14-02
provides:
  - endpoint status/payload parity assertions
  - auth/CSRF/rate-limit baseline parity checks
affects:
  - tests/parity/test_endpoint_middleware_parity.py
tech-stack:
  added: []
  patterns:
    - deterministic unauthenticated API/page parity checks
    - CSRF failure payload parity assertions
    - explicit runtime profile assertion for rate-limit baseline
key-files:
  created:
    - tests/parity/test_endpoint_middleware_parity.py
requirements-completed:
  - COMP-02
  - SEC-01
duration: 12 min
completed: 2026-04-16
---

# Phase 15 Plan 01: Endpoint and middleware parity

Implemented and executed parity tests validating critical endpoint status/payload behavior and middleware parity expectations after backend refactor.

## Execution Summary

- Start Time: 2026-04-16T05:05:00Z
- End Time: 2026-04-16T05:17:00Z
- Tasks Completed: 3/3

## Task Outcomes

### Task 1: Critical endpoint status and payload parity

- Added unauthorized API parity checks for:
  - `/api/workflows`
  - `/api/imports`
  - `/api/ai/history`
- Added protected page redirect parity checks for:
  - `/dashboard`
  - `/imports`
  - `/exports`

Verification:

- `python -m pytest tests/parity/test_endpoint_middleware_parity.py::test_unauthorized_api_returns_json_401 tests/parity/test_endpoint_middleware_parity.py::test_unauthorized_page_redirects_to_signin -q`

### Task 2: CSRF and rate-limit baseline parity

- Added CSRF failure parity test for `POST /api/workflows` (JSON 400 + message).
- Added explicit baseline test for current rate-limit profile behavior.

Verification:

- `python -m pytest tests/parity/test_endpoint_middleware_parity.py::test_api_csrf_failure_returns_json_400 tests/parity/test_endpoint_middleware_parity.py::test_rate_limit_profile_parity -q`

### Task 3: Full parity suite run

- Ran full endpoint/middleware parity module successfully.

Verification:

- `python -m pytest tests/parity/test_endpoint_middleware_parity.py -q`

## Deviations from Plan

None.

## Self-Check

- COMP-02 parity checks pass.
- SEC-01 parity checks pass.
