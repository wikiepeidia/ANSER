# Phase 12: Service Boundary Extraction - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract high-risk business logic from `app.py` handlers into explicit Flask-independent service modules while keeping route contracts stable and traceable. This phase does not move routes into blueprints (Phase 13) and does not change endpoint paths/methods.

</domain>

<decisions>
## Implementation Decisions

### Extraction Priority and Sequencing

- **D-01:** Extract critical domains first: workflow execution, AI job lifecycle, and Smart Import/Export transaction logic before lower-risk CRUD handlers.
- **D-02:** Keep route decorators and endpoint wiring in `app.py` during Phase 12; routes become thin wrappers that delegate to services.
- **D-03:** Use iterative domain slices (`extract -> service tests -> route delegation -> contract gate`) instead of one large migration.

### Route-to-Service Contract Style

- **D-04:** Service functions must accept plain Python inputs (dict/primitives/typed objects), never Flask `request`/session objects.
- **D-05:** Services return domain results (dict/typed structures) and raise typed service exceptions; HTTP status and response shaping stay in route handlers.
- **D-06:** Authentication, CSRF, and rate-limit enforcement remain at route/middleware layer in this phase.

### Handler Extraction Map (REFAC-06)

- **D-07:** Maintain a Phase 12 extraction map at `.planning/phases/12-service-boundary-extraction/12-handler-extraction-map.md`.
- **D-08:** Each map row records: current handler endpoint/function, target service module/function, delegation status, and linked service test coverage.

### Service-Layer Unit Test Scope (TEST-02)

- **D-09:** Prioritize unit tests for extracted high-risk service logic first (workflow, AI task state transitions, import/export rules), then expand to supporting domains.
- **D-10:** Keep Phase 11 contract smoke checks as the compatibility gate; Phase 12 adds service-layer pytest suites without replacing contract tests.

### Data Access Boundary During Extraction

- **D-11:** Reuse existing `core/database.py` abstractions in extracted services for this phase; do not introduce a new repository pattern yet.
- **D-12:** Consolidate duplicated query and business branches inside service modules while preserving SQLite/PostgreSQL compatibility behavior.

### the agent's Discretion

- Service module naming granularity and file-splitting details.
- Exception taxonomy used for route-level HTTP error mapping.
- Service test fixture internals, as long as tests remain Flask-independent at service layer.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Requirement Contracts

- `.planning/ROADMAP.md` — Phase 12 goal, requirement mapping (`REFAC-05`, `REFAC-06`, `TEST-02`), and success criteria.
- `.planning/REQUIREMENTS.md` — v3.0 requirement definitions and traceability status.
- `.planning/PROJECT.md` — milestone-level refactor constraints and branch strategy.
- `.planning/STATE.md` — active milestone state and continuity constraints.

### Baseline Guardrails from Phase 11

- `.planning/phases/11-baseline-contract-guardrails/11-CONTEXT.md` — locked baseline-contract decisions carried into extraction.
- `.planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json` — source-of-truth critical endpoint set.
- `scripts/phase11_route_snapshot.py` — route snapshot generation behavior for contract parity checks.
- `scripts/phase11_guardrail_check.py` — one-command baseline gate combining snapshot and contract tests.
- `tests/contracts/test_contract_routes.py` — manifest-driven route contract assertions.
- `tests/contracts/test_contract_smoke.py` — critical flow smoke assertions.
- `tests/conftest.py` — current pytest app/client fixture baseline.

### Existing Backend Extraction Surface

- `app.py` — current monolithic route and handler surface targeted for service extraction.
- `core/database.py` — dual SQLite/PostgreSQL abstraction used by route/business logic.
- `core/workflow_engine.py` — workflow orchestration logic to preserve while extracting route-level business code.
- `core/agent_middleware.py` — AI request normalization/orchestration logic relevant to service boundaries.
- `core/auth.py` — auth-layer behaviors that remain route/middleware-adjacent in Phase 12.
- `core/extensions.py` — extension setup patterns used by app factory and tests.
- `core/services/dl_client.py` — established service-client pattern to mirror for extracted service modules.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `core/database.py`: Existing DB compatibility layer can be consumed directly by extracted services.
- `core/workflow_engine.py`: Reusable workflow execution logic already separated from route declarations.
- `core/agent_middleware.py`: Existing AI middleware can anchor service boundaries for AI-related handlers.
- `scripts/phase11_guardrail_check.py`: Existing gate command can be reused after each extraction slice.

### Established Patterns

- Most route handlers currently live in `app.py`, with business operations mixed into HTTP handlers.
- Service-style modules already exist under `core/services/` and can be extended with domain-focused modules.
- Testing now has a stable pytest baseline for contracts; new Phase 12 tests should layer on this rather than replace it.

### Integration Points

- Route handlers remain in `app.py` this phase but delegate business branches to new service functions.
- Extracted services must plug into existing auth/session and DB patterns without endpoint signature changes.
- Contract guardrail command remains the parity checkpoint after each extraction increment.

</code_context>

<specifics>
## Specific Ideas

- Apply a "thin routes, explicit services" rule in Phase 12 while deferring route relocation to Phase 13.
- Use the handler extraction map as a live migration board that links each moved branch to service tests.
- Treat contract gate output as the stop/go checkpoint after each high-risk extraction slice.

</specifics>

<deferred>
## Deferred Ideas

- Blueprint/module route relocation and registration-order refactor (belongs to Phase 13).
- New repository/DAO abstraction layer beyond existing `core/database.py` compatibility shim (future hardening phase).
- Broad low-risk admin CRUD extraction before critical domains are stabilized.

</deferred>

---

*Phase: 12-service-boundary-extraction*
*Context gathered: 2026-04-16*
