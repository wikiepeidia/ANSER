# Phase 11 Migration Waves and Rollback Playbook

## Enforcement Policy

Phase 12 extraction is blocked until all Phase 11 gates pass.
Do not start route extraction, blueprint slicing, or service relocation until every wave below is marked PASS.

## Wave 1 Baseline Inventory

### Objectives

- Lock critical endpoint source-of-truth in manifest form.
- Generate a deterministic route snapshot from current Flask routing.

### Required Artifacts

- `.planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json`
- `scripts/phase11_route_snapshot.py`
- `.planning/phases/11-baseline-contract-guardrails/11-endpoint-snapshot.json`

### Gate

- Command:
  - `python scripts/phase11_route_snapshot.py --out .planning/phases/11-baseline-contract-guardrails/11-endpoint-snapshot.json`
- Pass Criteria:
  - Snapshot file is generated.
  - Snapshot summary shows `missing_paths: 0` and `method_mismatches: 0`.

### Rollback

- Trigger:
  - Snapshot generation fails or reports missing/mismatched critical contracts.
- Action:
  - Revert to last passing route baseline commit.
  - Re-run the snapshot command until summary is clean.

### Exit Criteria

- Manifest and snapshot are both present.
- Route baseline parity is verified with zero contract gaps.

## Wave 2 Test Guardrails

### Objectives

- Establish reproducible contract and smoke checks for critical backend paths.
- Confirm quick baseline validation command exits cleanly.

### Required Artifacts

- `pytest.ini`
- `tests/conftest.py`
- `tests/contracts/test_contract_routes.py`
- `tests/contracts/test_contract_smoke.py`

### Gate

- Command:
  - `python -m pytest tests/contracts -q`
- Pass Criteria:
  - Exit code is 0.
  - Contract and smoke tests for workflow, AI, and import/export groups pass.

### Rollback

- Trigger:
  - Any contract suite regression or flaky baseline failure.
- Action:
  - Revert to the last passing test baseline commit.
  - Re-run `python -m pytest tests/contracts -q` and only continue after stable pass.

### Exit Criteria

- Pytest contract command passes consistently.
- Baseline test harness is available for every subsequent refactor checkpoint.

## Wave 3 Pre-Extraction Freeze

### Objectives

- Combine route snapshot and contract tests into a single auditable gate.
- Produce phase evidence for extraction-readiness review.

### Required Artifacts

- `scripts/phase11_guardrail_check.py`
- `.planning/phases/11-baseline-contract-guardrails/11-guardrail-report.md`

### Gate

- Command:
  - `python scripts/phase11_guardrail_check.py`
- Pass Criteria:
  - Snapshot step passes.
  - Contract test step passes.
  - Report contains `Snapshot`, `Contract Tests`, and `Overall Gate` sections with PASS status.

### Rollback

- Trigger:
  - Guardrail script exits non-zero or report indicates FAIL.
- Action:
  - Stop extraction preparation immediately.
  - Roll back to the last commit where the guardrail script returned 0.
  - Re-run full guardrail command and regenerate report before any forward work.

### Exit Criteria

- Guardrail script returns exit code 0.
- Guardrail report is generated and stored as phase evidence.
- Phase 11 is explicitly marked ready for Phase 12 entry.
