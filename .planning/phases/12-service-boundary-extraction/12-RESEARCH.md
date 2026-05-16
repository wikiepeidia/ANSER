# Phase 12: Service Boundary Extraction - Research

**Date:** 2026-04-16
**Phase:** 12-service-boundary-extraction
**Goal:** Extract high-risk business logic from route handlers into Flask-independent services while preserving contract parity.

## Inputs Reviewed

- .planning/ROADMAP.md
- .planning/REQUIREMENTS.md
- .planning/PROJECT.md
- .planning/STATE.md
- .planning/phases/12-service-boundary-extraction/12-CONTEXT.md
- .planning/phases/11-baseline-contract-guardrails/11-CONTEXT.md
- app.py
- core/database.py
- core/workflow_engine.py
- core/agent_middleware.py
- core/services/dl_client.py
- tests/contracts/test_contract_routes.py
- tests/contracts/test_contract_smoke.py
- scripts/phase11_guardrail_check.py

## Key Findings

1. `app.py` contains route-level HTTP concerns and high-risk business logic in the same functions, especially around:
   - Workflow execution (`/api/workflow/execute`, `/api/workflows/*`)
   - AI chat/job lifecycle (`/api/ai/chat`, `/api/ai/status/<job_id>`, `/api/ai/history`)
   - Import/export transactional flows (`/api/imports`, `/api/exports`)
2. Existing service-pattern precedent is present in `core/services/dl_client.py`: Flask routes can stay thin while service modules handle domain behavior.
3. Data operations already depend on `core/database.py` compatibility shims and mixed SQLite/PostgreSQL placeholders, so introducing a new repository abstraction in this phase adds scope risk.
4. Phase 11 guardrails are operational and must remain the parity gate after each extraction increment.
5. Service-level unit testing scaffolding is still thin; Phase 12 should add focused tests for extracted high-risk logic first.

## Requirement-Focused Research Notes

### REFAC-05 (Business logic extracted into service modules)

Recommended strategy:

- Extract by domain slices, not by entire file rewrite.
- First targets:
  - Workflow route branch extraction into `core/services/workflow_service.py`
  - AI route branch extraction into `core/services/ai_chat_service.py`
  - Import/export transaction branches into `core/services/inventory_tx_service.py`
- Keep route decorators and HTTP response mapping in `app.py` for Phase 12.

### REFAC-06 (Handler extraction map)

Recommended artifact:

- `.planning/phases/12-service-boundary-extraction/12-handler-extraction-map.md`
- Required columns:
  - Endpoint path + method
  - Current handler function
  - Target service function
  - Delegation status (`pending`, `delegated`, `verified`)
  - Test reference

This map should be updated in every extraction plan to preserve migration traceability.

### TEST-02 (Service-layer unit tests)

Recommended baseline:

- Add `tests/services/` test suite with Flask-independent service tests.
- Unit-test extracted logic directly, not through route test clients.
- Keep contract gate command:
  - `python scripts/phase11_guardrail_check.py`
- Add service quick command:
  - `python -m pytest tests/services -q`

## Extraction Hotspot Inventory (from current code)

### Workflow Domain

- `run_workflow()` currently performs token parse + execution call + HTTP shaping in one route.
- Workflow persistence handlers (`get_user_workflows`, `save_workflow`, `delete_workflow`, `get_single_workflow`) combine DB queries and serialization in route body.

### AI Domain

- Background job orchestration (`background_ai_task`) mixes:
  - DB history operations
  - remote AI request construction
  - middleware action processing
  - file-based job state persistence
- Route endpoints (`ai_chat`, `get_chat_history`, `ai_job_status`, `clear_chat_history`) mix input validation, DB operations, and asynchronous dispatch.

### Import/Export Domain

- `api_create_import` and `api_create_export` include transaction boundaries, stock checks, product creation, and automation triggers directly in route handlers.
- These handlers are high-risk because they mutate inventory and related transaction tables.

## Common Pitfalls and Mitigations

- Pitfall: Moving route functions and service extraction in same phase creates churn.
  - Mitigation: Keep route location stable in Phase 12; only delegate business branches.
- Pitfall: Service signatures leak Flask/request context, reducing testability.
  - Mitigation: Enforce plain-Python inputs/outputs and typed exceptions.
- Pitfall: Extraction map becomes stale and unusable.
  - Mitigation: Make map update a mandatory task in each plan that moves logic.
- Pitfall: Unit tests pass but endpoint behavior drifts.
  - Mitigation: Run Phase 11 guardrail check after each extraction wave.

## Validation Architecture

Validation dimensions for this phase:

- Dimension A: Service boundary clarity (`app.py` handlers delegate instead of owning business logic)
- Dimension B: Traceability (`12-handler-extraction-map.md` tracks every migrated handler)
- Dimension C: Service testability (service-layer pytest suite exists and passes)
- Dimension D: Contract parity (Phase 11 guardrail check remains green)

Verification strategy:

- Quick service loop: `python -m pytest tests/services -q`
- Guardrail parity loop: `python scripts/phase11_guardrail_check.py`
- Artifact checks:
  - `12-handler-extraction-map.md` exists and includes delegated handlers
  - `core/services/*_service.py` files exist for migrated domains
  - plan-specific service tests exist under `tests/services/`

## Research Outcome

## RESEARCH COMPLETE

Phase 12 should proceed with three sequential plans:

1. Establish extraction map and service-test foundation.
2. Extract workflow + AI high-risk logic into service modules with direct unit coverage.
3. Extract import/export transaction logic into service modules, update map statuses, and enforce guardrail parity.
