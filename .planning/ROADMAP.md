# Roadmap: ANSER

## Phases

- [x] **Phase 1-10: Feature Foundation (Archived)** - Core features implementation.
- [x] **Phase 11-15: Backend Refactor (Archived)** - Transitioning to modular monolith.
- [x] **Phase 16: Planning Context Refresh** - Align .planning docs with Engineering reality.
- [ ] **Phase 18: Focused Regression Hardening** - Add/update targeted tests.
- [ ] **Phase 20: AI Route Decoupling (BE-01)** - Resolve circular imports in AI routes.
- [ ] **Phase 21: Auth & User Consolidation (BE-02)** - Centralize User/Auth logic.
- [ ] **Phase 22: Dependency & Service Isolation (BE-04)** - Cleanup requirements and isolate dl_service.
- [ ] **Phase 23: Optimization & Caching (BE-05)** - Optimize product catalog and workflow queue.
- [ ] **Phase 24: Async Task Infrastructure (BE-07)** - Implement background queue for AI/OCR.

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
**Plans**:
- [ ] 20-01-PLAN.md — Circular Import Resolution

### Phase 21: Auth & User Consolidation
**Goal**: Ensure a single, consistent source of truth for user data and authentication.
**Depends on**: Phase 20
**Requirements**: FR-AUTH-05 (BE-02)
**Success Criteria**:
  1. User repository logic is consolidated into a single service/module.
  2. Authentication (Login/Register/OAuth) works consistently across all application routes.
**Plans**: TBD

### Phase 22: Dependency & Service Isolation
**Goal**: Streamline the project environment and prepare `dl_service` for independent scaling.
**Depends on**: Phase 21
**Requirements**: NFR-INF-01 (BE-04)
**Success Criteria**:
  1. `requirements.txt` is refactored, removing unused packages and separating dev dependencies.
  2. `dl_service` can be started and run in an isolated environment with its own dependency subset.
**Plans**: TBD

### Phase 23: Optimization & Caching
**Goal**: Improve system performance for high-volume retail data and complex workflows.
**Depends on**: Phase 22
**Requirements**: NFR-PERF-04 (BE-05)
**Success Criteria**:
  1. Product catalog retrieval time is significantly reduced through effective caching.
  2. Workflow engine queue supports concurrent execution without thread starvation or blocking.
**Plans**: TBD

### Phase 24: Async Task Infrastructure
**Goal**: Decouple long-running operations from the request-response cycle.
**Depends on**: Phase 23
**Requirements**: NFR-PERF-05 (BE-07)
**Success Criteria**:
  1. AI processing and OCR jobs are offloaded to a background task queue (e.g., Celery or internal thread pool).
  2. Users receive immediate job IDs and can poll for status updates or receive notifications.
**Plans**: TBD

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1-15  | N/A            | Archived | 2026-04-22 |
| 16    | 1/1            | Complete | 2026-06-08 |
| 18    | 0/1            | Not started | - |
| 20    | 0/1            | In progress | - |
| 21    | 0/1            | Not started | - |
| 22    | 0/1            | Not started | - |
| 23    | 0/1            | Not started | - |
| 24    | 0/1            | Not started | - |

---
*Last updated: 2026-06-08*
