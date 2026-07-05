# Requirements: ANSER

This document tracks the functional and non-functional requirements for ANSER, derived from the PRD, codebase analysis, and current project goals.

## Functional Requirements

### 1. Authentication & User Management

- **FR-AUTH-01**: Users can register and log in with email and password.
- **FR-AUTH-02**: Users can log in via Google OAuth.
- **FR-AUTH-03**: Password verification supports secure hashing (bcrypt) and legacy version fallback.
- **FR-AUTH-04**: Session management supports "remember me" and CSRF protection.
- **FR-AUTH-05**: (BE-02) Consolidated User repository and authentication logic for consistency across services.

### 2. AI Chat & Agent Integration

- **FR-AI-01**: Users can interact with an AI agent through a web-based chat interface.
- **FR-AI-02**: The AI agent can process non-trivial requests as background tasks (Job system).
- **FR-AI-03**: The AI agent can perform actions within the application via `AgentMiddleware` (e.g., query database, trigger workflows).
- **FR-AI-04**: Support for Vision-enabled agents to process image uploads.
- **FR-AI-05**: (BE-01) AI routes are free of circular imports and architectural bottlenecks.

### 3. Deep Learning Services (OCR & Forecast)

- **FR-DL-01**: Users can upload invoice images for automated field extraction (OCR).
- **FR-DL-02**: OCR fallback chain ensures processing across multiple engines (EasyOCR, PaddleOCR, VietOCR, etc.).
- **FR-DL-03**: System provides LSTM-based forecasting for inventory/sales quantities.
- **FR-DL-04**: Forecast results are accessible via REST API and can be used in workflows.

### 4. Workflow Automation

- **FR-WORK-01**: Users can create automation workflows using a drag-and-drop builder.
- **FR-WORK-02**: Workflows are represented as Directed Acyclic Graphs (DAGs).
- **FR-WORK-03**: Support for multiple node types: Google Drive/Sheets/Docs/Gmail, Webhooks, Notifications, Filters, OCR, and Forecast.
- **FR-WORK-04**: Manual and scheduled/triggered execution of workflows.

### 5. Retail & Operations Management

- **FR-OPS-01**: Manage products, customers, and inventory levels.
- **FR-OPS-02**: Record and track sales and invoices.
- **FR-OPS-03**: Wallet and subscription system for user tiers/credits.
- **FR-OPS-04**: "Smart Import" and "Smart Export" for bulk data operations.

## Non-Functional Requirements

### Performance & Scaling

- **NFR-PERF-01**: Main app response time < 500ms for standard API calls.
- **NFR-PERF-02**: AI chat responses (greetings) return in < 2s; background jobs provide status updates.
- **NFR-PERF-03**: OCR processing for a single invoice should complete within 10s.
- **NFR-PERF-04**: (BE-05) Product catalog caching and workflow engine queue optimization for high-volume data.
- **NFR-PERF-05**: (BE-07) Background task queue implementation for AI/OCR services to prevent request blocking.

### Stability & Infrastructure

- **NFR-STAB-01**: Backend must maintain the v3.0 refactored structure (isolated route/service modules).
- **NFR-STAB-02**: No new bugs introduced in the core auth and workflow flows.
- **NFR-STAB-03**: Touched code must have associated pytest coverage.
- **NFR-INF-01**: (BE-04) Refactored dependencies (requirements.txt) and isolated `dl_service` environment.

### Security

- **NFR-SEC-01**: All sensitive integrations (Google, AI) must use environment variables or secure `secrets/` storage.
- **NFR-SEC-02**: CSRF protection enabled for all state-changing operations.
- **NFR-SEC-03**: Role-based access control (RBAC) enforced on admin and operation routes.

## Traceability

| ID | Phase | Status |
| --- | --- | --- |
| FR-AUTH-01-04 | 1-5 (Archived) | Complete |
| FR-AI-01-04 | 6-10 (Archived) | Complete |
| FR-DL-* | 6-10 (Archived) | Complete |
| FR-WORK-* | 1-10 (Archived) | Complete |
| FR-OPS-* | 1-10 (Archived) | Complete |
| NFR-STAB-01 | Phase 11-15 | Complete |
| NFR-STAB-02 | Phase 17 (Skipped) | Cancelled |
| NFR-STAB-03 | Phase 18 | Complete |
| FR-AI-05 (BE-01) | Phase 20 | Complete |
| FR-AUTH-05 (BE-02) | Phase 21 | Complete |
| NFR-INF-01 (BE-04) | Phase 22 | Complete |
| NFR-PERF-04 (BE-05) | Phase 23 | Complete |
| NFR-PERF-05 (BE-07) | Phase 24 | Complete |
| CIRC-01 | Phase 25 | Complete |
| CIRC-02 | Phase 25 | Complete |
| CIRC-03 | Phase 25 | Complete |
| NFR-TD-01 | Phase 25 | Complete |
| NFR-TD-02 | Phase 25 | Complete |
| AUTO-01 | Phase 26 | Complete |
| AUTO-02 | Phase 26 | Complete |
| DL-01 | Phase 27 | Complete |
| DL-02 | Phase 27 | Complete |
| DL-03 | Phase 27 | Complete |
| HYG-01 | Phase 28 | Complete |
| HYG-02 | Phase 28 | Complete |
| HYG-03 | Phase 28 | Complete |

---

## Milestone v1.1 Requirements — Tech Debt Completion

### Circular Import & Module Decoupling

- [x] **CIRC-01**: Developer can import `app` without triggering server startup (`python -c "import app"` exits cleanly with no server spin-up)
- [x] **CIRC-02**: System can be served via gunicorn using a `wsgi.py` entry point (`wsgi.py` exists and exports `application`)
- [x] **CIRC-03**: `core/services/dl_client.py` uses HTTP by default (`use_local=False`); no `sys.path.insert` in `core/`; local mode imports lazily only when explicitly requested

### Automation Engine Schema Fix

- [x] **AUTO-01**: `automation_engine.py` SQL references only columns/tables that exist in the actual schema (no `suppliers` table query, no `import_price` column access)
- [x] **AUTO-02**: Low-stock automation and scheduled import run end-to-end without exception on both SQLite and NeonDB

### DL Service Logging & OCR Validation

- [x] **DL-01**: All `print()` calls in `core/services/dl_client.py` replaced with `get_logger()` from `core.logger`
- [x] **DL-02**: OCR end-to-end flow returns valid `invoice_data` JSON structure from `/api/model1/detect`
- [x] **DL-03**: `dl_service` starts independently via `python run_dl_service.py` without requiring the Flask main app

### Code Hygiene

- [x] **HYG-01**: `core/services/analytics_service.py` uses `get_logger()`, removes duplicate `except` block, reads `GA_PROPERTY_ID` from `Config` instead of hardcoded value
- [x] **HYG-02**: `core/google_integration.py` `list_files` correctly escapes single quotes in Drive API queries
- [x] **HYG-03**: `core/utils.py` `format_workspace_tree` accesses row fields by name (not tuple index)

### Non-Functional

- [x] **NFR-TD-01**: `grep sys.path core/` returns no results after Phase 25
- [x] **NFR-TD-02**: No new circular import errors introduced; existing routes remain functional

---

Last updated: 2026-06-14 (Phase 28 complete — v1.1 milestone done)

---

## Milestone v1.2 Requirements — Security & Ownership Hardening

### Environment & Transport Security

- [x] **SEC-01**: Production and staging-like environments enable secure session cookies, rate limiting, HTTPS enforcement, and strict transport security by default, while `dev`/`test` remain explicitly opt-out for local workflows

### Ownership & Tenant Scoping

- [x] **OWN-01**: User can delete a sale only when the sale belongs to that user
- [x] **OWN-02**: User can list, update, and delete products only within their ownership or authorized role scope
- [x] **OWN-03**: User can list, update, and delete customers only within their ownership or authorized role scope
- [x] **OWN-04**: Reports and scheduled report generation only include data owned by the current user or workspace
- [x] **OWN-05**: Automation rules execute only against data and resources owned by the current user or workspace

### Authentication & Integration Security

- [x] **AUTH-06**: Google-created accounts store passwords using `AuthManager.hash_password` so subsequent password setup and password login use the same bcrypt flow
- [x] **SEC-02**: User-configured webhooks reject destinations that resolve to private, loopback, or link-local IP ranges before any outbound request is made
- [x] **SEC-03**: Authenticated state-changing routes use CSRF protection unless they are verified third-party webhook endpoints

### Error Handling & Upload Validation

- [x] **SEC-04**: Global and route-level error handlers return safe client responses without raw exception strings and include a correlation identifier for server-side diagnostics
- [x] **SEC-05**: Upload endpoints reject files that exceed configured size limits or unsupported MIME/extension allowlists with clear validation responses

### Data Access & Runtime Consistency

- [x] **PLAT-01**: Remaining route modules stop using imported database globals and instead resolve the database manager from `current_app.extensions`
- [x] **PLAT-02**: Google OAuth persistence logic uses repository methods instead of route-level raw SQL for user and workspace writes
- [x] **PLAT-03**: Deployment/runtime documentation and checks confirm the RQ worker process is present for queued AI chat jobs

### Non-Functional

- [x] **NFR-SEC-04**: Every ownership or security fix includes regression coverage proving unauthorized access, unsafe webhook targets, or invalid uploads are rejected
- [x] **NFR-OPS-01**: Worker/runtime verification leaves operators with a concrete way to detect and prevent stuck queued AI jobs

## v2 / Deferred from TODO.MD

None currently. All items in `TODO.MD` were pulled into milestone v1.2.

## Out of Scope for v1.2

| Feature | Reason |
|---------|--------|
| New end-user feature development | This milestone is reserved for backend hardening and platform safety work from `TODO.MD` |
| UI redesign or product expansion | No related backlog items exist in `TODO.MD`; keep scope on correctness and security |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEC-01 | Phase 29 | Complete |
| OWN-01 | Phase 30 | Complete |
| OWN-02 | Phase 30 | Complete |
| OWN-03 | Phase 30 | Complete |
| OWN-04 | Phase 30 | Complete |
| OWN-05 | Phase 30 | Complete |
| AUTH-06 | Phase 31 | Complete |
| SEC-02 | Phase 31 | Complete |
| SEC-03 | Phase 31 | Complete |
| SEC-05 | Phase 31 | Complete |
| SEC-04 | Phase 32 | Complete |
| PLAT-01 | Phase 32 | Complete |
| PLAT-02 | Phase 32 | Complete |
| PLAT-03 | Phase 33 | Complete |
| NFR-SEC-04 | Phase 33 | Complete |
| NFR-OPS-01 | Phase 33 | Complete |

**Coverage:**
- v1.2 requirements: 16 total
- Mapped to phases: 16
- Unmapped: 0 ✓

---

Last updated: 2026-07-05 (milestone v1.2 implemented and verified)
