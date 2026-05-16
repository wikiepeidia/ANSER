# Phase 11: Baseline Contract Guardrails - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock backend contracts before extraction by defining a critical endpoint baseline, runnable guardrail checks, and rollback-aware migration guardrails so Phase 12 can move code safely.

</domain>

<decisions>
## Implementation Decisions

### Critical Endpoint Baseline Scope

- **D-01:** Baseline coverage is the core refactor-critical set only: Auth, Workflow execution, AI chat/status, and Smart Import/Export APIs.
- **D-02:** For non-API page routes, baseline checks track presence/status only for key pages: `/`, `/dashboard`, `/imports`, `/exports`.
- **D-03:** Guardrail pass criteria at this phase use method+path+status with minimal response-shape checks (key top-level fields), not deep payload-value assertions.
- **D-04:** Source of truth for critical endpoints is a versioned manifest in `.planning`, validated against a generated route snapshot on each guardrail run.

### the agent's Discretion

- Exact manifest schema and snapshot tooling details are open to standard implementation during planning, as long as D-04 remains enforceable.
- Internal test fixture style (Flask app fixture, data seeding style, mocking level) is open to standard pytest practices while preserving D-01 to D-03.
- Migration wave/rollback mechanics were not discussed in this run and can be proposed during planning under SAFE-01 constraints.

</decisions>

<canonical_refs>

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Constraints

- `.planning/ROADMAP.md` — Phase 11 goal, requirements mapping, and success criteria.
- `.planning/REQUIREMENTS.md` — TEST-01, TEST-03, SAFE-01 contract for this phase.
- `.planning/PROJECT.md` — Milestone-level constraints (backend-branch isolation, maintainability-first objective).
- `.planning/STATE.md` — Current milestone status and active execution position.

### Existing Backend Contract Surface

- `app.py` — Current route surface and app-factory/bootstrap patterns that Phase 11 guardrails must protect.
- `core/extensions.py` — Existing extension-init pattern to keep stable while adding test harnesses.
- `core/auth.py` — Auth behaviors/decorators that inform baseline auth contract checks.
- `core/workflow_engine.py` — Workflow execution behavior likely to be covered by critical contract tests.
- `core/agent_middleware.py` — AI workflow/chat parsing path relevant to core contract baseline.

</canonical_refs>

<code_context>

## Existing Code Insights

### Reusable Assets

- `app.py:create_app()` already centralizes app initialization and can be reused for Flask test client setup.
- `core/extensions.py` provides singleton extension objects (`login_manager`, `csrf`, `limiter`, `db_manager`) compatible with app-factory tests.
- Existing async AI job handling in `app.py` (`AI_JOBS` + status endpoints) provides direct targets for characterization checks.

### Established Patterns

- Most HTTP contracts still live in `app.py` with `@app.route` decorators, indicating contract drift risk is concentrated in one file.
- Route behavior commonly returns JSON dicts with `success`/`message` conventions, useful for minimal response-shape assertions.
- Current testing is mostly script-based (`test/`, `dl_service/test_*.py`) with no established pytest baseline yet.

### Integration Points

- Auth contract touchpoints: `/auth/*`, `/api/session`, and profile/settings APIs.
- Workflow contract touchpoints: `/api/workflows`, `/api/workflow/execute`, and upload helpers.
- AI contract touchpoints: `/api/ai/chat`, `/api/ai/status/<job_id>`, `/api/ai/history`.
- Smart Import/Export touchpoints: `/api/imports`, `/api/exports`, and key page routes `/imports`, `/exports`.

</code_context>

<specifics>
## Specific Ideas

- Keep Phase 11 intentionally narrow and enforceable so Phase 12 extraction starts with stable baseline guardrails rather than broad pre-refactor overhead.

</specifics>

<deferred>
## Deferred Ideas

### Deferred Within Milestone

- Endpoint inventory artifact format details beyond D-04 (exact schema/representation) were not discussed in this run.
- Test guardrail depth beyond minimal response-shape assertions was not discussed in this run.
- Migration wave and rollback policy details were not discussed in this run.

None of these are out-of-scope for v3.0; they are deferred to Phase 11 planning details.

</deferred>

---

*Phase: 11-baseline-contract-guardrails*
*Context gathered: 2026-04-16*
