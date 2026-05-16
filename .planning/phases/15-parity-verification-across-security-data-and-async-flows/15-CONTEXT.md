# Phase 15: Parity Verification Across Security, Data, and Async Flows - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning and execution
**Mode:** Autonomous (Phase 15 only fallback)

<domain>
## Phase Boundary

Verify post-refactor behavioral parity for endpoint status/payload contracts, middleware behavior (auth/CSRF/rate-limit), critical DB write paths across SQLite and PostgreSQL modes, and async AI job lifecycle states.

</domain>

<decisions>
## Implementation Decisions

### Contract and Middleware Parity

- **D-01:** Add dedicated parity tests for critical endpoint behavior using Flask test client with no authentication state.
- **D-02:** Validate unauthorized API behavior returns JSON 401 and protected page behavior redirects to sign-in.
- **D-03:** Validate CSRF failure path on non-exempt API POST returns JSON 400 with expected error payload.
- **D-04:** Rate-limit parity baseline is documented/tested as disabled in current backend profile unless explicitly enabled in runtime config.

### Data and Async Parity

- **D-05:** Validate critical DB write query compatibility in both SQLite and PostgreSQL paths by testing PGShim placeholder translation and commit behavior.
- **D-06:** Validate async AI lifecycle states pending/processing/completed/failed through service + route helper tests with isolated mocks.

### Safety and Scope

- **D-07:** Verification-first phase: no feature additions; only parity tests and evidence artifacts.
- **D-08:** Use local deterministic mocks for external AI/DB dependencies to avoid flaky network coupling.

### the agent's Discretion

- Exact test case decomposition and fixture layout.
- Minor test-only helper abstractions for readability.

</decisions>

<canonical_refs>

## Canonical References

- .planning/ROADMAP.md
- .planning/REQUIREMENTS.md
- .planning/STATE.md
- .planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json
- tests/contracts/test_contract_routes.py
- tests/contracts/test_contract_smoke.py
- tests/services/test_ai_chat_service.py
- routes/ai_routes.py
- core/database.py

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- Contract manifest and smoke tests already cover route presence and broad status families.
- Service tests already cover extraction-layer behavior for workflow/AI/inventory.
- Coverage and guardrail gates are established from Phase 14.

### Gaps This Phase Must Close

- Contract payload parity (not only status families).
- Explicit middleware parity assertions for auth + CSRF + rate-limit expectation.
- DB write-path parity assertions across SQLite and PostgreSQL compatibility paths.
- Async AI lifecycle parity assertions for all required job states.

### Integration Points

- Unauthorized handler in app factory controls JSON 401 vs redirect behavior.
- CSRF error handler controls API error JSON shape.
- Database PGShim provides placeholder translation and insert handling.
- ai_chat_service and routes.ai_routes helper functions define async lifecycle transitions.

</code_context>

<specifics>
## Specific Ideas

- Add `tests/parity/test_endpoint_middleware_parity.py` for COMP-02 + SEC-01.
- Add `tests/parity/test_data_async_parity.py` for DATA-01 + DATA-02.
- Keep tests network-free via monkeypatch and deterministic fakes.

</specifics>

<deferred>
## Deferred Ideas

- End-to-end mixed-branch parity validation with UI interactions (outside backend-only phase).
- Production rate-limit tuning and strict threshold rollout (post-parity hardening).

</deferred>

---

*Phase: 15-parity-verification-across-security-data-and-async-flows*
*Context gathered: 2026-04-16*
