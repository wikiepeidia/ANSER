# Roadmap: ANSER

## Phases

- [x] **Phase 1-10: Feature Foundation (Archived)** - Core features implementation.
- [x] **Phase 11-15: Backend Refactor (Archived)** - Transitioning to modular monolith.
- [x] **Phase 16: Planning Context Refresh** - Align .planning docs with Engineering reality.
- [x] **Phase 18: Focused Regression Hardening** - Add/update targeted tests. (completed 2026-06-14)
- [x] **Phase 20: AI Route Decoupling (BE-01)** - Resolve circular imports in AI routes.
- [x] **Phase 21: Auth & User Consolidation (BE-02)** - Centralize User/Auth logic.
- [x] **Phase 22: Dependency & Service Isolation (BE-04)** - Cleanup requirements and isolate dl_service.
- [x] **Phase 23: Optimization & Caching (BE-05)** - Optimize product catalog and workflow queue.
- [x] **Phase 24: Async Task Infrastructure (BE-07)** - Implement background queue for AI/OCR.

---

### Milestone v1.1: Tech Debt Completion

- [x] **Phase 25: Circular Import & Module Decoupling** - Remove module-level app instantiation, create wsgi.py, eliminate sys.path hacks. (completed 2026-06-14)
- [x] **Phase 26: Automation Engine Schema Fix** - Fix schema mismatches in automation_engine.py; add smoke test. (completed 2026-06-14)
- [x] **Phase 27: DL Service Logging & OCR Validation** - Replace print() with logger in dl_client; validate OCR end-to-end flow. (completed 2026-06-14)
- [x] **Phase 28: Code Hygiene** - Fix analytics_service, google_integration, and utils.py outstanding bugs. (completed 2026-06-14)

## Phase Details

### Phase 18: Focused Regression Hardening

**Goal**: Secure the refactored boundaries with automated tests.
**Depends on**: Phase 16
**Requirements**: NFR-STAB-03
**Success Criteria**:

1. Pytest coverage increased for all touched service slices.
2. Route ownership notes updated in codebase/CONVENTIONS.md.

**Plans**: 1 plan

Plans:

- [x] 18-01-PLAN.md — Repair regression test suite (33→0 failures) and add route ownership notes

### Phase 20: AI Route Decoupling

**Goal**: Resolve architectural bottlenecks and circular imports in the AI service layer.
**Depends on**: Phase 16
**Requirements**: FR-AI-05 (BE-01)
**Success Criteria**:

1. `ai_routes.py` and associated services can be imported without circular dependency errors.
2. AI Chat interface remains fully functional with verified backend responses.

**Plans**: Completed

### Phase 21: Auth & User Consolidation

**Goal**: Ensure a single, consistent source of truth for user data and authentication.
**Depends on**: Phase 20
**Requirements**: FR-AUTH-05 (BE-02)
**Success Criteria**:

1. User repository logic is consolidated into a single service/module.
2. Authentication (Login/Register/OAuth) works consistently across all application routes.

**Plans**: Completed

### Phase 22: Dependency & Service Isolation

**Goal**: Streamline the project environment and prepare `dl_service` for independent scaling.
**Depends on**: Phase 21
**Requirements**: NFR-INF-01 (BE-04)
**Success Criteria**:

1. `requirements.txt` is refactored, removing unused packages and separating dev dependencies.
2. `dl_service` can be started and run in an isolated environment with its own dependency subset.

**Plans**: Completed

### Phase 23: Optimization & Caching

**Goal**: Improve system performance for high-volume retail data and complex workflows.
**Depends on**: Phase 22
**Requirements**: NFR-PERF-04 (BE-05)
**Success Criteria**:

1. Product catalog retrieval time is significantly reduced through effective caching.
2. Workflow engine queue supports concurrent execution without thread starvation or blocking.

**Plans**: Completed

### Phase 24: Async Task Infrastructure

**Goal**: Decouple long-running operations from the request-response cycle.
**Depends on**: Phase 23
**Requirements**: NFR-PERF-05 (BE-07)
**Success Criteria**:

1. AI processing and OCR jobs are offloaded to a background task queue (Redis/RQ).
2. Users receive immediate job IDs and can poll for status updates or receive notifications.

**Plans**: Completed

---

### Phase 25: Circular Import & Module Decoupling

**Goal**: Remove module-level `app = create_app()` from app.py, introduce a proper wsgi.py entry point, and eliminate all sys.path hacks so the module graph is clean and importable without side effects.
**Depends on**: Phase 24
**Requirements**: CIRC-01, CIRC-02, CIRC-03, NFR-TD-01, NFR-TD-02
**Success Criteria** (what must be TRUE):

1. `python -c "import app"` exits cleanly with no server spin-up and no error output.
2. `grep sys.path core/` returns no results — no sys.path manipulation exists anywhere under core/.
3. `wsgi.py` exists at the project root and exports an `application` object compatible with gunicorn.
4. `core/services/dl_client.py` defaults to `use_local=False`; local-mode imports occur only when explicitly requested.

**Plans**: 1 plan

Plans:

- [x] 25-01-PLAN.md — Remove module-level app instantiation, create wsgi.py, eliminate sys.path hacks

### Phase 26: Automation Engine Schema Fix

**Goal**: Fix automation_engine.py so it only references tables and columns that exist in the actual SQLite and NeonDB schemas, and prove the fix with a runnable smoke test.
**Depends on**: Phase 25
**Requirements**: AUTO-01, AUTO-02
**Success Criteria** (what must be TRUE):

1. `automation_engine.py` contains no reference to the `suppliers` table or the `import_price` column.
2. `check_low_stock` runs end-to-end against a test database without raising an exception.
3. `execute_scheduled_import` runs end-to-end against a test database without raising an exception.

**Plans**: 1 plan

Plans:

- [x] 26-01-PLAN.md — Fix schema mismatches and add automation smoke test

### Phase 27: DL Service Logging & OCR Validation

**Goal**: Replace informal print() debugging in the DL client and service with structured logging, and confirm that the full OCR pipeline works without coupling dl_service to the Flask main app.
**Depends on**: Phase 25
**Requirements**: DL-01, DL-02, DL-03
**Success Criteria** (what must be TRUE):

1. No `print()` calls remain in `core/services/dl_client.py`; all log output goes through `get_logger()`.
2. An OCR upload to `/api/model1/detect` returns a valid `invoice_data` JSON structure with recognized fields.
3. `python run_dl_service.py` starts the DL service without importing the Flask main app.

**Plans**: 1 plan

Plans:

- [x] 27-01-PLAN.md — Replace DL runtime prints with logging and validate OCR/forecast contracts

### Phase 28: Code Hygiene

**Goal**: Close the remaining code-quality bugs in analytics_service.py, google_integration.py, and utils.py that were deferred from earlier phases.
**Depends on**: Phase 25
**Requirements**: HYG-01, HYG-02, HYG-03
**Success Criteria** (what must be TRUE):

1. `analytics_service.py` uses `get_logger()`, has no duplicate except block, and reads `GA_PROPERTY_ID` from `Config`.
2. `google_integration.py` `list_files` correctly escapes single quotes in Drive API query strings.
3. `utils.py` `format_workspace_tree` accesses row fields by name, not by tuple index.

**Plans**: 1 plan

Plans:

- [x] 28-01-PLAN.md — Fix analytics Config/logger, Drive query escaping, workspace named-field access

## Progress Table

| Phase | Plans Complete | Status      | Completed  |
|-------|----------------|-------------|------------|
| 1-15  | N/A            | Archived    | 2026-04-22 |
| 16    | 1/1            | Complete    | 2026-06-08 |
| 18    | 1/1            | Complete    | 2026-06-14 |
| 20    | 1/1            | Complete    | 2026-06-08 |
| 21    | 1/1            | Complete    | 2026-06-08 |
| 22    | 1/1            | Complete    | 2026-06-08 |
| 23    | 1/1            | Complete    | 2026-06-08 |
| 24    | 1/1            | Complete    | 2026-06-08 |
| 25    | 1/1            | Complete    | 2026-06-14 |
| 26    | 1/1            | Complete    | 2026-06-14 |
| 27    | 1/1            | Complete    | 2026-06-14 |
| 28    | 1/1            | Complete    | 2026-06-14 |

---

Last updated: 2026-06-14 (v1.1 milestone complete — all Phases 25-28 done)

---

### Milestone v1.2: Security & Ownership Hardening

- [x] **Phase 29: Production Security Defaults** - Gate production-only security config by environment and prove rate limiting/login hardening works in practice. (completed 2026-07-05)
- [x] **Phase 30: Ownership Enforcement Across Operations** - Apply owner/workspace scoping to sales, products, customers, reports, and automation data flows. (completed 2026-07-05)
- [x] **Phase 31: Integration Security Hardening** - Fix Google-account password hashing, webhook SSRF protection, CSRF exemptions, and upload validation gaps. (completed 2026-07-05)
- [x] **Phase 32: Error Handling & Data Access Cleanup** - Stop leaking exceptions to clients and finish route/repository consistency cleanup. (completed 2026-07-05)
- [x] **Phase 33: Queue Runtime Verification & Regression Coverage** - Verify AI queue worker operations and lock in regression tests for the new hardening work. (completed 2026-07-05)

## Phase Details

### Phase 29: Production Security Defaults

**Goal**: Make the default runtime safe outside `dev`/`test` by enforcing secure transport/session settings and validating that brute-force protection is actually active on login.
**Depends on**: Phase 28
**Requirements**: SEC-01
**Success Criteria**:

1. Production-like config enables `SESSION_COOKIE_SECURE`, rate limiting, HTTPS redirect behavior, and HSTS by default without breaking `dev`/`test`.
2. Login abuse testing proves the limiter on the authentication route returns `429` after repeated attempts.
3. Configuration behavior is documented clearly enough for deployers to understand which environment flags change security posture.

**Plans**: 1 plan

Plans:

- [x] 29-01-PLAN.md - Secure runtime defaults and verify limiter wiring

### Phase 30: Ownership Enforcement Across Operations

**Goal**: Close cross-tenant data access gaps by ensuring sales, products, customers, reports, and automation behavior all honor user/workspace ownership.
**Depends on**: Phase 29
**Requirements**: OWN-01, OWN-02, OWN-03, OWN-04, OWN-05
**Success Criteria**:

1. A user cannot delete another user's sale.
2. Product and customer CRUD paths reject unauthorized list/update/delete access.
3. Reporting and automation flows do not read or act on data outside the current user's or workspace's scope.

**Plans**: 1 plan

Plans:

- [x] 30-01-PLAN.md - Owner-scope sales, catalog, reports, and automations

### Phase 31: Integration Security Hardening

**Goal**: Remove remaining security inconsistencies across external integrations, request validation, and upload entry points.
**Depends on**: Phase 30
**Requirements**: AUTH-06, SEC-02, SEC-03, SEC-05
**Success Criteria**:

1. Google-created accounts can set and use passwords through the same bcrypt-based flow as regular accounts.
2. Webhook destinations resolving to private, loopback, or link-local addresses are blocked before network access.
3. Only true third-party webhook endpoints remain CSRF-exempt, and upload endpoints enforce clear size/type validation.

**Plans**: 1 plan

Plans:

- [x] 31-01-PLAN.md - Harden Google OAuth, webhooks, CSRF, and uploads

### Phase 32: Error Handling & Data Access Cleanup

**Goal**: Standardize safe error responses and remove the remaining route-level data access shortcuts that bypass project conventions.
**Depends on**: Phase 31
**Requirements**: SEC-04, PLAT-01, PLAT-02
**Success Criteria**:

1. Clients no longer receive raw exception text from global handlers or the specifically noted routes.
2. Remaining route modules resolve shared database access through `current_app.extensions` instead of imported globals.
3. Google OAuth user/workspace persistence logic lives in repository abstractions rather than route-level raw SQL.

**Plans**: 1 plan

Plans:

- [x] 32-01-PLAN.md - Safe API errors and route/repository cleanup

### Phase 33: Queue Runtime Verification & Regression Coverage

**Goal**: Ensure queued AI work cannot silently stall in deployment and preserve the hardening work with targeted automated coverage.
**Depends on**: Phase 32
**Requirements**: PLAT-03, NFR-SEC-04, NFR-OPS-01
**Success Criteria**:

1. Operators have a concrete documented check for whether the RQ worker process is running for queued AI jobs.
2. Regression tests cover unauthorized access rejection, unsafe webhook blocking, and upload validation behavior introduced in v1.2.
3. Deployment/runtime notes make the failure mode for missing workers visible before jobs accumulate indefinitely.

**Plans**: 1 plan

Plans:

- [x] 33-01-PLAN.md - Queue worker guard and regression coverage

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 29 | 1/1 | Complete | 2026-07-05 |
| 30 | 1/1 | Complete | 2026-07-05 |
| 31 | 1/1 | Complete | 2026-07-05 |
| 32 | 1/1 | Complete | 2026-07-05 |
| 33 | 1/1 | Complete | 2026-07-05 |

---

Last updated: 2026-07-05 (v1.2 milestone implemented and verified)
