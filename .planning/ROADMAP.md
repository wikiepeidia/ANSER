# Roadmap: ANSER

## Phases

- [x] **Phase 1-10: Feature Foundation (Archived)** - Core features implementation.
- [x] **Phase 11-15: Backend Refactor (Archived)** - Transitioning to modular monolith.
- [x] **Phase 16: Planning Context Refresh** - Align .planning docs with Engineering reality.
- [ ] **Phase 18: Focused Regression Hardening** - Add/update targeted tests.
- [x] **Phase 20: AI Route Decoupling (BE-01)** - Resolve circular imports in AI routes.
- [x] **Phase 21: Auth & User Consolidation (BE-02)** - Centralize User/Auth logic.
- [x] **Phase 22: Dependency & Service Isolation (BE-04)** - Cleanup requirements and isolate dl_service.
- [x] **Phase 23: Optimization & Caching (BE-05)** - Optimize product catalog and workflow queue.
- [x] **Phase 24: Async Task Infrastructure (BE-07)** - Implement background queue for AI/OCR.

---

### Milestone v1.1: Tech Debt Completion

- [x] **Phase 25: Circular Import & Module Decoupling** - Remove module-level app instantiation, create wsgi.py, eliminate sys.path hacks. (completed 2026-06-14)
- [x] **Phase 26: Automation Engine Schema Fix** - Fix schema mismatches in automation_engine.py; add smoke test. (completed 2026-06-14)
- [ ] **Phase 27: DL Service Logging & OCR Validation** - Replace print() with logger in dl_client; validate OCR end-to-end flow.
- [ ] **Phase 28: Code Hygiene** - Fix analytics_service, google_integration, and utils.py outstanding bugs.

## Phase Details

### Phase 18: Focused Regression Hardening

**Goal**: Secure the refactored boundaries with automated tests.
**Depends on**: Phase 16
**Requirements**: NFR-STAB-03
**Success Criteria**:

1. Pytest coverage increased for all touched service slices.
2. Route ownership notes updated in codebase/CONVENTIONS.md.

**Plans**: TBD

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

**Plans**: TBD

### Phase 28: Code Hygiene

**Goal**: Close the remaining code-quality bugs in analytics_service.py, google_integration.py, and utils.py that were deferred from earlier phases.
**Depends on**: Phase 25
**Requirements**: HYG-01, HYG-02, HYG-03
**Success Criteria** (what must be TRUE):

1. `analytics_service.py` uses `get_logger()`, has no duplicate except block, and reads `GA_PROPERTY_ID` from `Config`.
2. `google_integration.py` `list_files` correctly escapes single quotes in Drive API query strings.
3. `utils.py` `format_workspace_tree` accesses row fields by name, not by tuple index.

**Plans**: TBD

## Progress Table

| Phase | Plans Complete | Status      | Completed  |
|-------|----------------|-------------|------------|
| 1-15  | N/A            | Archived    | 2026-04-22 |
| 16    | 1/1            | Complete    | 2026-06-08 |
| 18    | 0/1            | Not started | -          |
| 20    | 1/1            | Complete    | 2026-06-08 |
| 21    | 1/1            | Complete    | 2026-06-08 |
| 22    | 1/1            | Complete    | 2026-06-08 |
| 23    | 1/1            | Complete    | 2026-06-08 |
| 24    | 1/1            | Complete    | 2026-06-08 |
| 25    | 1/1            | Complete    | 2026-06-14 |
| 26    | 1/1            | Complete    | 2026-06-14 |
| 27    | 0/1            | Not started | -          |
| 28    | 0/1            | Not started | -          |

---

Last updated: 2026-06-14 (v1.1 Phase 26 complete)
