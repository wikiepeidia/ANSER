# Discussion Log - Phase 13

Date: 2026-04-16
Mode: Autonomous fallback (non-interactive)
Phase: 13 - Blueprint Migration and Composition Root Finalization

## Inputs Considered

- Prior phase context from 11 and 12
- Existing extraction state in app.py and routes/*
- Phase11 manifest and guardrail constraints
- User direction: continue cleanup and revamp app.py overall

## Grey Areas Resolved

### Area 1: Blueprint partition strategy

Decision: Domain-based modules aligned to service boundaries and operational concerns.
Accepted set:

- routes/workflow_routes.py
- routes/ai_routes.py
- routes/inventory_routes.py
- routes/dl_routes.py
- routes/wallet_routes.py
- routes/google_routes.py
- routes/main_routes.py (migration bridge)

### Area 2: Registration strategy

Decision: Deterministic composition-root ordering in create_app.
Order:

1. auth blueprint
2. inventory blueprint
3. workflow blueprint
4. ai blueprint
5. dl blueprint
6. register_main_routes(app)

### Area 3: Endpoint compatibility

Decision: Preserve existing path/method contracts and endpoint names used by templates.
Implementation note: register_main_routes(app) binds legacy handlers directly on app to avoid endpoint prefix drift.

### Area 4: Safety gate

Decision: Keep mandatory parity checks after extraction slices.
Gate commands:

- python -m pytest tests/services/test_inventory_route_delegation.py tests/services/test_workflow_service.py tests/services/test_ai_chat_service.py -q
- python -m pytest tests/contracts/test_contract_routes.py tests/contracts/test_contract_smoke.py -q
- python scripts/phase11_route_snapshot.py && python scripts/phase11_guardrail_check.py

## Deferred Ideas

- Break main_routes into smaller domain modules in a subsequent cleanup pass.
- Remove app-module global bridging once route ownership stabilizes.

## Outcome

Context ready and phase execution evidence recorded under 13-01 summary + verification.
