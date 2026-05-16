# Phase 13: Blueprint Migration and Composition Root Finalization - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning and execution
**Mode:** Autonomous (next-phase fallback due milestone-init non-TTY)

<domain>
## Phase Boundary

Migrate route ownership out of monolithic app.py into dedicated route modules and keep app.py as composition/bootstrap root while preserving endpoint contracts.

</domain>

<decisions>
## Implementation Decisions

### Blueprint Partition Strategy

- **D-01:** Use domain-based route modules aligned to existing service boundaries: workflow, AI, inventory, DL, wallet/subscription, Google OAuth/API, and remaining legacy surface in main routes.
- **D-02:** Keep auth routes under existing auth blueprint to avoid login-flow endpoint drift.

### Composition Root and Registration

- **D-03:** app.py remains the composition root: create app, bind extensions, register blueprints/routes in deterministic order.
- **D-04:** Registration order is fixed as: auth -> inventory -> workflow -> ai -> dl -> main route registrar.

### Endpoint Contract Preservation

- **D-05:** Preserve path/method contracts exactly; no URL shape changes during extraction.
- **D-06:** Preserve endpoint names used by templates (e.g., google_login) by registering remaining main routes directly on app via register_main_routes(app), not via prefixed blueprint endpoint names.

### Migration Safety and Verification

- **D-07:** Extract in thin slices with parity checks after each slice: service/delegation tests, contract tests, route snapshot, guardrail gate.
- **D-08:** Treat phase11 manifest + guardrail as stop/go contract for Phase 13.

### the agent's Discretion

- Further decomposition of routes/main_routes.py into additional domain modules after Phase 13 minimums are satisfied.
- Internal helper placement and import tidying while maintaining startup stability.

</decisions>

<canonical_refs>

## Canonical References

- .planning/ROADMAP.md
- .planning/STATE.md
- .planning/REQUIREMENTS.md
- .planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json
- scripts/phase11_route_snapshot.py
- scripts/phase11_guardrail_check.py
- tests/contracts/test_contract_routes.py
- tests/contracts/test_contract_smoke.py

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- Existing extracted service modules under core/services support route-level delegation.
- Phase11 guardrail scripts provide parity evidence with stable contracts.
- tests/services contains route-delegation and service tests for extracted domains.

### Established Patterns

- Route extraction follows domain modules under routes/.
- app.py keeps extension setup, auth blueprint, and central registration.
- Incremental extraction plus immediate test/guardrail validation is the default safety pattern.

### Integration Points

- app.py create_app registration block is the composition choke point.
- routes/main_routes.py acts as migration bridge for still-unmoved routes.
- wallet and google routes are delegated from main_routes to dedicated route registrars.

</code_context>

<specifics>
## Specific Ideas

- Keep endpoint compatibility as hard constraint over aesthetic refactor purity.
- Prefer deterministic registration and explicit module ownership for jury explainability.
- Avoid introducing new product behavior in this phase.

</specifics>

<deferred>
## Deferred Ideas

- Split the remaining large main_routes module into pages/admin/workspace submodules (next cleanup slice).
- Introduce stronger import boundaries to remove app-module global bridging after Phase 13 stabilization.

</deferred>

---

*Phase: 13-blueprint-migration-and-composition-root-finalization*
*Context gathered: 2026-04-16*
