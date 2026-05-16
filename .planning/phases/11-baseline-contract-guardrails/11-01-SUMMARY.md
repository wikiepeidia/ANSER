---
phase: 11-baseline-contract-guardrails
plan: 01
subsystem: testing
tags: [pytest, flask, contracts, smoke, guardrails]
requires: []
provides:
  - Endpoint manifest for critical baseline routes
  - Route snapshot generator for contract drift detection
  - Pytest contract and smoke suite for baseline behavior
affects: [11-02, phase-12-extraction, backend-refactor]
tech-stack:
  added: [pytest.ini]
  patterns: [manifest-driven route assertions, app-url-map snapshot baseline]
key-files:
  created:
    - .planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json
    - .planning/phases/11-baseline-contract-guardrails/11-endpoint-snapshot.json
    - scripts/phase11_route_snapshot.py
    - pytest.ini
    - tests/conftest.py
    - tests/contracts/test_contract_routes.py
    - tests/contracts/test_contract_smoke.py
  modified: []
key-decisions:
  - "Use module-level app when available, fallback to create_app, to align tests with runtime route wiring"
  - "Keep contract tests manifest-driven to detect path/method drift with minimal payload coupling"
patterns-established:
  - "Route baseline snapshots are generated from Flask url_map and persisted for deterministic comparisons"
  - "Critical endpoint checks run through a single pytest contracts entrypoint"
requirements-completed: [TEST-01, TEST-03]
duration: 3 min
completed: 2026-04-16
---

# Phase 11 Plan 01: Baseline Contract Guardrails Summary

**Manifest-driven route contract guardrails were established with executable snapshot generation and a passing baseline smoke suite for critical backend endpoints.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-16T03:00:21Z
- **Completed:** 2026-04-16T03:03:12Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added a curated endpoint manifest covering auth, workflow, AI, import/export, and key page routes.
- Implemented `phase11_route_snapshot.py` to collect current path/method contracts from the app route map and emit a deterministic snapshot.
- Added pytest baseline harness and contract smoke suite; `python -m pytest tests/contracts -q` passes.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create critical endpoint manifest and route snapshot generator** - `c79eaad` (feat)
2. **Task 2: Add repository pytest harness and contract tests for critical endpoints** - `6406fb3` (test)

**Plan metadata:** `N/A` (planning files are gitignored in this repository)

## Files Created/Modified

- `.planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json` - Curated source-of-truth list of critical endpoint contracts.
- `.planning/phases/11-baseline-contract-guardrails/11-endpoint-snapshot.json` - Generated baseline comparison artifact with path/method parity summary.
- `scripts/phase11_route_snapshot.py` - Deterministic route snapshot generator for manifest drift checks.
- `pytest.ini` - Repository pytest discovery and execution defaults for contract tests.
- `tests/conftest.py` - Shared Flask app/client fixtures for contract and smoke checks.
- `tests/contracts/test_contract_routes.py` - Manifest-driven path/method assertions against runtime route map.
- `tests/contracts/test_contract_smoke.py` - Lightweight status and minimal-shape smoke checks across critical groups.

## Decisions Made

- Use the module-level Flask app if present (same as runtime wiring), with `create_app` fallback for test fixture resilience.
- Use manifest-defined smoke endpoints and expected status windows to reduce brittle deep-payload assertions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Snapshot script could not import app module from scripts directory**

- **Found during:** Task 1 (snapshot command verification)
- **Issue:** Running `python scripts/phase11_route_snapshot.py` failed with module import errors.
- **Fix:** Added project-root path bootstrap to `sys.path` before importing app module.
- **Files modified:** `scripts/phase11_route_snapshot.py`
- **Verification:** Snapshot command executed successfully and wrote output JSON.
- **Committed in:** `c79eaad`

**2. [Rule 1 - Bug] Method mismatch false positives for duplicate-path rules**

- **Found during:** Task 1 (snapshot output validation)
- **Issue:** Route collection overwrote methods when multiple rules shared the same path.
- **Fix:** Changed route collection logic to merge methods per path.
- **Files modified:** `scripts/phase11_route_snapshot.py`
- **Verification:** Snapshot summary reported `missing_paths: 0` and `method_mismatches: 0`.
- **Committed in:** `c79eaad`

**3. [Rule 3 - Blocking] Contract tests used partial route registry from app factory fixture**

- **Found during:** Task 2 (`python -m pytest tests/contracts -q`)
- **Issue:** Fixture created an app instance missing runtime route registrations, causing broad 404 failures.
- **Fix:** Updated test fixture to prefer module-level `app` and fallback to `create_app`.
- **Files modified:** `tests/conftest.py`
- **Verification:** `python -m pytest tests/contracts -q` passed (10/10).
- **Committed in:** `6406fb3`

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All auto-fixes were required for reproducible contract verification; scope stayed within Plan 11-01.

## Issues Encountered

- Git ignore rules excluded `tests/`; task commit used force-add for plan-owned files only.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Baseline manifest, snapshot generator, and contract/smoke checks are in place.
- Ready for Plan 11-02 to add migration wave governance and single-command guardrail report generation.

---
*Phase: 11-baseline-contract-guardrails*
*Completed: 2026-04-16*
