# Phase 11: Baseline Contract Guardrails - Research

**Date:** 2026-04-16
**Phase:** 11-baseline-contract-guardrails
**Goal:** Establish baseline contracts and test guardrails before backend extraction.

## Inputs Reviewed

- .planning/ROADMAP.md
- .planning/REQUIREMENTS.md
- .planning/PROJECT.md
- .planning/STATE.md
- .planning/phases/11-baseline-contract-guardrails/11-CONTEXT.md
- app.py
- core/extensions.py
- core/auth.py
- core/workflow_engine.py
- core/agent_middleware.py
- core/services/dl_client.py

## Key Findings

1. Current backend contract surface is concentrated in app.py, with critical routes for:
   - Auth session and Google login callbacks
   - Workflow CRUD and execute endpoints
   - AI chat/upload/history/status endpoints
   - Smart Import/Export APIs and core pages
2. There is no repository-level pytest harness yet (no pytest.ini and no pyproject.toml test config).
3. Existing tests are script-style and fragmented (test/, dl_service/test_*.py), so Phase 11 must create a clear backend contract baseline from scratch.
4. App factory already exists (create_app), which enables Flask test-client based characterization tests without starting full services.

## Requirement-Focused Research Notes

### TEST-01 (Pytest tooling configured)

Recommended baseline:

- Add pytest configuration using pytest.ini at repository root.
- Add tests/conftest.py that builds app test client from create_app.
- Ensure quick command is stable on backend branch:
  - python -m pytest tests/contracts -q

### TEST-03 (Smoke and contract tests for critical flows)

Recommended contract scope (per context decisions D-01 to D-04):

- Auth: /api/session and Google auth routes presence
- Workflow: /api/workflows GET/POST, /api/workflow/execute POST
- AI: /api/ai/chat, /api/ai/status/<job_id>, /api/ai/history
- Smart Import/Export: /api/imports and /api/exports plus key page presence checks (/dashboard, /imports, /exports, /)

Recommended assertion depth:

- Route exists + expected method
- Expected status class or status code
- Minimal top-level response-shape checks only (e.g., success/message keys when applicable)

### SAFE-01 (Wave migration and rollback points)

Recommended wave policy for Phase 11 artifacts:

- Wave 1: Inventory/manifest + snapshot scripts (no runtime behavior change)
- Wave 2: Pytest harness + contract smoke suite
- Wave 3: Rollback playbook and baseline freeze evidence

Rollback points:

- After each wave, capture passing test proof and manifest snapshot.
- If next wave fails, revert to previous passing wave commit and re-run quick baseline command.

## Recommended Artifacts for Planning

1. Contract Manifest
   - .planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json
   - Curated critical endpoints and expected methods/check semantics

2. Generated Snapshot
   - .planning/phases/11-baseline-contract-guardrails/11-endpoint-snapshot.json
   - Produced from route-introspection script to detect drift

3. Baseline Test Harness
   - pytest.ini
   - tests/conftest.py
   - tests/contracts/test_contract_routes.py
   - tests/contracts/test_contract_smoke.py

4. Rollback/Migration Guardrail Document
   - .planning/phases/11-baseline-contract-guardrails/11-migration-waves.md

## Common Pitfalls and Mitigations

- Pitfall: Over-scoping all app.py endpoints in Phase 11.
  - Mitigation: Stick to core contract set from context D-01.
- Pitfall: Brittle deep payload assertions before refactor starts.
  - Mitigation: Keep minimal response-shape checks only in Phase 11.
- Pitfall: External service side effects in tests (Google/DL).
  - Mitigation: Use monkeypatch/mocks and local app factory test client.
- Pitfall: Treating route inventory as static handwritten docs.
  - Mitigation: Use curated manifest + generated snapshot comparison.

## Validation Architecture

Validation dimensions for this phase:

- Dimension A: Tooling readiness (pytest config + deterministic command)
- Dimension B: Contract guardrail coverage (critical endpoints present and testable)
- Dimension C: Drift detection mechanism (manifest vs generated snapshot)
- Dimension D: Safe extraction readiness (wave checkpoints + rollback playbook)

Verification strategy:

- Quick loop command: python -m pytest tests/contracts -q
- Wave gate command: python -m pytest tests/contracts -q && python -m pytest test/test_ai_service.py -q
- Artifact checks:
  - endpoint manifest exists
  - endpoint snapshot exists
  - migration waves document exists

## Research Outcome

## RESEARCH COMPLETE

Phase 11 can proceed with two to three executable plans that implement:

- Baseline contract inventory and drift snapshot
- Pytest harness and critical-flow contract smoke tests
- Migration wave and rollback guardrails
