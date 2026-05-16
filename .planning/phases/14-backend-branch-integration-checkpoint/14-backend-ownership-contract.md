# Phase 14 Backend Ownership Contract

Status: active
Scope: Backend branch integration checkpoint
Last Updated (UTC): 2026-04-16T04:24:02Z

## Ownership Boundaries

This contract protects backend refactor integrity before mixed-branch merge preparation.

Allowed backend ownership areas:

- `app.py` composition/bootstrap and backend registration wiring.
- `core/` backend domain logic, services, workflow engine, auth, DB abstraction.
- `routes/` backend route modules and registration adapters.
- `tests/services/`, `tests/contracts/`, and backend guardrail scripts.
- `.planning/phases/11-*`, `.planning/phases/14-*` evidence and checkpoint artifacts.

Prohibited overlap during Phase 14 backend checkpoint:

- UI layout and styling changes under `ui/templates/` and `static/css/`.
- Frontend behavior changes in `static/js/` not required for backend parity gates.
- Mixed-branch merge execution itself (this phase only prepares merge-readiness evidence).

Reviewer expectations:

- Backend gate evidence must be attached for each checkpoint claim.
- Contract and guardrail regressions block merge-preparation sign-off.

## Mixed-Branch Merge Contract

Merge preparation between backend and UI branches can proceed only when all backend prerequisites below are met.

Sequencing contract:

1. Complete Phase 14 backend coverage and ownership checkpoint documents.
2. Re-run backend quality gates on latest backend HEAD.
3. Freeze backend branch for merge-prep window (no unreviewed backend behavior changes).
4. Execute mixed-branch merge in a dedicated merge-prep phase with rollback plan.

Non-negotiable constraints:

- No silent endpoint contract changes.
- No bypass of guardrail script when preparing merge.
- No direct edits to security-sensitive auth/csrf/rate-limit behavior without parity tests.

## Required Gates

All gates must pass in the same checkpoint cycle:

- Coverage gate (enforceable threshold):
  - `python scripts/phase14_backend_coverage_gate.py --threshold 20`
- Backend service/contract regression suite:
  - `python -m pytest tests/services tests/contracts -q`
- Baseline route contract guardrail:
  - `python scripts/phase11_guardrail_check.py`

Gate result policy:

- Any failure blocks merge-preparation readiness.
- Gate reruns must update phase-local evidence artifacts before re-approval.

## Rollback Trigger

Rollback Trigger conditions:

- Coverage gate falls below enforced threshold.
- Contract tests fail or endpoint parity drift appears.
- Guardrail check reports missing route or method mismatch.

Rollback action sequence:

1. Stop merge-preparation activities immediately.
2. Revert or isolate the failing backend change set.
3. Re-run all required gates from a clean state.
4. Update checkpoint evidence with failure root cause and fix confirmation.
