# Domain Pitfalls: Backend Refactor + Testability Milestone (Flask Monolith)

**Context:** Existing production-like feature surface, active demo pressure, and a milestone that must refactor `app.py`, extract routes/services, add tests, and preserve behavior.
**Researched:** 2026-04-14
**Confidence:** HIGH (based on direct inspection of `.planning/PROJECT.md`, `app.py`, `core/`, `routes/`, `services/`)

## Risk-Prioritized Pitfalls

Phase mapping used below:
- Phase 1: Foundation and Branch Safety
- Phase 2: Service Layer Extraction
- Phase 3: Blueprint Route Extraction
- Phase 4: App Factory Wiring and Tests
- Phase 5: Documentation and Demo Freeze

| Priority | Severity | Pitfall | Why it happens | Early warning signal | Prevention strategy | Roadmap phase that should absorb it |
|---|---|---|---|---|---|---|
| P1 | Critical | Route contract drift from overlapping endpoints | `app.py` currently defines overlapping paths (for example `/api/products` and `/api/customers` are registered in multiple handlers). Refactor changes registration order and can silently change which handler answers. | Same endpoint returns a different payload shape/status code after extraction; unexpected 404/405 on previously valid calls. | Build a route inventory and response-contract baseline before moving code. Consolidate to one canonical handler per path+method, then extract. Add contract tests for top endpoints. | Phase 1 (inventory) + Phase 3 (route extraction) |
| P2 | Critical | Hidden global dependency coupling (`auth_manager`, `google`, `automation_engine`, `JOBS_DIR`, plan constants) | Many handlers reference module-level mutable globals initialized by `create_app()`. During extraction/imports these can be `None` or duplicated. | `NoneType` errors in routes/tests, inconsistent runtime state between modules, duplicate job directory logic. | Move runtime dependencies to `current_app.extensions` accessors and explicit service objects. Keep only immutable constants at module scope. Ban routes importing mutable globals from `app.py`. | Phase 1 + Phase 2 |
| P3 | Critical | Import-time side effects make tests and startup non-deterministic | `app = create_app()` executes at import time; OAuth/secret loading and job folder creation run immediately; external clients can initialize during import. | Test collection fails before tests run; importing app requires secrets/network; slow/flaky startup. | Enforce pure app factory usage in tests (`create_app(test_config)`), lazy-load integrations, and a strict `TestingConfig` that disables network/external auth by default. | Phase 1 + Phase 4 |
| P4 | Critical | No real regression safety net before refactor | Existing `test/` is mostly script-style/manual checks, not pytest characterization coverage for current behavior. | Refactor "looks clean" but login/workflow/AI/OCR/wallet regress in integration demo. | Write characterization tests first (current behavior snapshots for critical routes), then refactor behind those tests. Gate merges on this suite. | Phase 1 + Phase 4 |
| P5 | High | Incomplete service extraction (Flask objects leak into services) | Copy-paste from handlers tends to keep `request`, `current_user`, `jsonify`, session logic inside service code. | Service unit tests require app/request context; services import Flask or `app.py`; circular import pressure increases. | Define service boundary contract: plain inputs, plain outputs, no Flask imports. Add CI check (`grep`/lint) that fails if `services/` imports Flask. | Phase 2 |
| P6 | High | Auth/authorization behavior drift after blueprint split | Endpoint renaming and decorator relocation change redirect/login/error behavior (`url_for`, `login_view`, role checks). | Redirect loops, `BuildError` for endpoint names, APIs returning HTML redirect instead of JSON 401/403. | Maintain endpoint rename map, auth matrix tests (unauthenticated/unauthorized/authorized), and smoke tests for signin, admin workspace, and API auth semantics. | Phase 3 + Phase 4 |
| P7 | High | Middleware parity loss (CSRF, limiter, unauthorized handlers) | Decorators and global handlers are easy to miss when code is moved file-by-file. | Previously working POSTs fail with CSRF 400, rate-limits disappear, API unauthorized format changes. | Keep a middleware manifest and parity test list for protected endpoints. Treat security decorators and handlers as migration-critical assets, not incidental code. | Phase 3 + Phase 4 |
| P8 | High | SQLite/PostgreSQL compatibility regressions hidden by local-only checks | Large amount of raw SQL in handlers with shimmed placeholder translation; behavior differs across engines and schemas. | Works on SQLite, fails on Postgres/Neon with SQL or type errors. | Move DB logic into service/repository modules and run dual-engine smoke checks for critical flows (auth, products/customers, workflows, wallet/subscription). | Phase 2 + Phase 4 |
| P9 | Medium | Async AI job subsystem corruption/race issues during extraction | File-based job state is threaded and duplicated in module scope (`JOBS_DIR` logic appears more than once). Refactor can split helpers incorrectly. | Random "job not found", malformed job JSON, stuck `processing` states. | Create a single `JobStore` service with atomic write pattern and lock discipline; add lifecycle tests for submit -> poll -> complete/fail. | Phase 2 + Phase 4 |
| P10 | Medium | External integration side effects pollute unit tests | Auth and workflow paths invoke network-backed functions (Google, email, webhook, DL client) with mixed mock fallback behavior. | Unit tests become flaky, slow, or accidentally hit live services. | Dependency-inject integration adapters and provide deterministic fakes in test fixtures; separate unit vs integration test markers. | Phase 2 + Phase 4 |
| P11 | Medium | Branch integration churn under demo pressure | Large `app.py` edits and parallel UI work increase merge-conflict risk and accidental behavior drops. | Repeated conflict resolution in the same hotspots, rising hotfix count, delayed merge confidence. | Use vertical-slice PRs (one domain at a time), daily rebase/sync, and explicit ownership of touched modules per phase. | Phase 1 (branch policy) + ongoing through Phases 2-4 |

## Top 5 Must-Avoid Failures

1. Refactoring routes before freezing and testing current API contracts.
2. Keeping mutable runtime dependencies as module globals in route files.
3. Declaring refactor done without pytest characterization coverage on jury-critical flows.
4. Moving handlers into services while keeping Flask context objects inside those services.
5. Validating only on SQLite and discovering Postgres breakage at integration/demo time.
