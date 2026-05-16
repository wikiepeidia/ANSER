# Architecture Integration Plan: Milestone v3.0 Backend Refactor

**Project:** ANSER / Group Project AI-ML (Flask monolith + DL microservice)
**Date:** 2026-04-14
**Scope:** Move `app.py` to composition-only (app factory + registration), move handlers to route modules/blueprints, move business logic to services, preserve current behavior.

## Current Baseline (Code Audit)

- `app.py` already has `create_app()` and extension init but still contains almost all route handlers.
- Only one blueprint currently registered in main app: `auth_bp`.
- Main app route modules under `routes/` are currently empty.
- Main app service modules under `services/` are currently empty.
- Existing reusable core services already available: `core/services/dl_client.py`, `core/services/analytics_service.py`, plus `core/auth.py`, `core/workflow_engine.py`, `core/automation_engine.py`, `core/agent_middleware.py`, `core/database.py`.
- Current risk profile is not a new architecture build. It is a strangler refactor of a live monolith with mixed SQL, session logic, OAuth, async job workers, and external service calls.

## Integration Points (Must Stay Stable)

1. Flask app bootstrap and extension binding
   - Keep exact initialization order from current `create_app()`:
     - config loading
     - OAuth setup
     - security middleware
     - login manager/csrf/limiter/database extension binding
   - Preserve `login_manager.login_view = 'auth.signin'`.

2. Dependency access contract
   - Current code uses module-level globals (`auth_manager`, `automation_engine`, `agent_middleware`, `google`, `db_manager` alias `db`).
   - Refactor target should shift to app-scoped dependencies via `current_app.extensions[...]` and thin dependency getters.

3. Authentication/authorization behavior
   - Preserve current role checks and response style:
     - browser routes redirect + flash
     - API routes return JSON 401/403
   - Preserve current session behavior (`PERMANENT_SESSION_LIFETIME`, `session.permanent`, remember login).

4. Database compatibility surface
   - Keep `core/database.py` interface untouched during route/service migration (`get_connection`, table column checks, workflow helpers).
   - Preserve SQL behavior and transaction boundaries. Avoid schema changes in this milestone.

5. OAuth and Google integrations
   - Keep callback URLs and endpoints unchanged (`/auth/connect/google`, `/auth/login/google`, `/auth/google/callback`).
   - Preserve token persistence model (`users.google_token`, `users.google_email`).

6. Workflow execution contract
   - Keep `/api/workflow/execute` payload shape and `core/workflow_engine.execute_workflow(...)` call contract unchanged.
   - Keep node execution semantics and return format stable.

7. AI async job contract
   - Preserve job lifecycle (`pending`, `processing`, `completed`, `failed`) and file-based job storage under `jobs/`.
   - Preserve endpoint contracts:
     - `POST /api/ai/chat`
     - `GET /api/ai/status/<job_id>`
     - history endpoints

8. DL proxy behavior
   - Preserve current DL proxy endpoints and response envelope (`success`, `data` or `error`) using `DLClient`.
   - Do not change timeout/default URL behavior in this milestone.

9. Template/page routing and endpoint names
   - Preserve `url_for(...)` targets used by templates and redirects.
   - If endpoint function names change after blueprint migration, define explicit endpoint names to avoid broken navigation.

10. Route precedence and duplicates (critical)

- Current monolith contains duplicate URL+method handlers (`/api/customers`, `/api/products`, and subscription extension variants).
- Migration must decide canonical handlers deliberately. Accidental reordering can change behavior without obvious code errors.

## New vs Modified Components

| Component | Type | Purpose | Compatibility Notes |
|---|---|---|---|
| `app.py` | Modified | Composition root only: create app, bind extensions, register blueprints, error handlers | Keep `app = create_app()` export for current run/deploy style |
| `routes/__init__.py` | New | Central blueprint registration (`register_blueprints(app)`) | Registration order must preserve current route precedence |
| `routes/auth_routes.py` | New (first extracted) | Auth + OAuth routes | Preserve existing endpoint names used by `url_for` |
| `routes/pages_routes.py` | New | Render-only pages (`/workspace`, `/dashboard`, etc.) | No business logic in route body |
| `routes/workflow_routes.py` | New | Workspace/scenario/workflow APIs | Keep current JSON shape and status codes |
| `routes/inventory_routes.py` | New | Products/customers/import/export/sales/report APIs | Handle duplicate legacy handlers with explicit canonical choice |
| `routes/admin_routes.py` | New | Admin users/roles/analytics endpoints | Preserve current role gate behavior |
| `routes/billing_routes.py` | New | Wallet/subscription endpoints | High-risk domain; migrate later |
| `routes/ai_routes.py` | New | AI chat/upload/history/status | Keep async job contract stable |
| `routes/dl_routes.py` | New | DL detect/forecast proxy endpoints | Keep request/response envelopes unchanged |
| `services/` domain modules | New | Move business logic and SQL out of routes | Functions accept primitive inputs, return data/errors, no Flask globals |
| `core/dependencies.py` (or similar) | New | Typed getters for app-scoped dependencies | Replaces module-level global coupling incrementally |
| `tests/backend/smoke/` | New | Behavior lock tests for key flows before and after extraction | Must validate response codes and payload shape parity |
| Legacy route bundle (`routes_legacy/` or `app_legacy.py`) | Optional New | Fast fallback switch if regressions appear | Enable domain rollback by config flag |

## Data and Control Flow Impacts

### Before (current)

Request -> app.py route -> mixed validation + role checks + SQL + external calls + response building

### After (target)

Request -> blueprint route handler -> service function -> core/db/external integration -> route response adapter

### Impact details

1. Request validation moves earlier and becomes consistent
   - Route layer owns HTTP parsing and status code mapping.
   - Service layer owns domain validation and business rules.

2. SQL execution moves out of route functions
   - Transactions and DB error handling are centralized per domain service.
   - Easier unit testing and lower accidental copy/paste divergence.

3. Session/auth context becomes explicit
   - Route extracts `current_user.id`, role, token/session flags.
   - Service receives only required values (no direct `current_user` dependency).

4. Error mapping becomes deterministic
   - Service returns structured result/error type.
   - Route maps to existing HTTP code conventions to preserve behavior.

5. Async control flow for AI is isolated
   - Thread/job management moves to AI service module.
   - Route remains stable API facade.

6. OAuth control flow remains route-owned for Flask-login/session
   - Token normalization/persistence can be delegated to service helper.
   - `login_user`, flash, redirect stay in route layer to avoid Flask context leakage.

7. Endpoint stability requirement
   - URL paths, methods, and response payload keys must remain byte-compatible where possible.
   - Explicit compatibility wrappers are preferred over clean rewrite.

## Suggested Build Order (Safe Integration Sequence)

### Phase 0: Behavior Lock Baseline (no architecture move yet)

- Capture endpoint inventory from current app (`app.url_map`) and commit it.
- Add smoke tests for critical flows:
  - auth sign-in/sign-out + oauth callback path
  - workflow CRUD + execute
  - AI chat submit/status/history
  - wallet topup + admin pending approval + subscription upgrade
  - DL detect endpoint
- Snapshot representative JSON responses for key endpoints.
- Backup local sqlite DB file before migration waves.

### Phase 1: Composition Hardening in app.py

- Keep `create_app()` as the only bootstrapping function.
- Introduce `register_blueprints(app)` call (initially only auth).
- Add dependency getter utilities so new modules can avoid module-level globals.
- Keep all existing route handlers in `app.py` for now except auth (already blueprint-based).

### Phase 2: Service Extraction In Place (routes still in app.py)

- Domain-by-domain, extract business logic from route function bodies into `services/...`.
- Keep route decorators and URLs in `app.py`; route bodies become thin adapters calling services.
- Recommended wave order (low to high risk):
  1. render-only pages + session/settings/profile
  2. workspace/scenario/workflow CRUD
  3. inventory/products/customers/import/export/sales/reports/automations
  4. admin user/role/activity endpoints
  5. billing (wallet/subscription)
  6. oauth/google integration helpers
  7. ai async worker and upload
  8. dl proxy
- After each wave: run smoke tests and compare payload snapshots.

### Phase 3: Blueprint Migration (move handlers from app.py to routes/)

- For each domain wave:
  - create blueprint module in `routes/`
  - move existing thin route handlers with minimal edits
  - register blueprint in `register_blueprints(app)`
  - remove migrated handlers from `app.py`
- Preserve endpoint names with explicit `endpoint=` where templates/redirects rely on old names.
- Maintain registration order intentionally to preserve route precedence.

### Phase 4: Duplicate Route Resolution and Canonicalization

- Identify duplicate URL+method handlers migrated from `app.py`.
- Select canonical handler per duplicated endpoint.
- If behavior differs, keep compatibility wrapper that preserves currently observed behavior.
- Add regression tests specifically for formerly duplicated endpoints.

### Phase 5: Finalize Composition-Only app.py

- `app.py` should contain:
  - config/bootstrap
  - extension binding
  - dependency registration
  - context processors + error handlers
  - blueprint registration
  - module export (`app = create_app()`) and `if __name__ == '__main__'` run block
- No business SQL or domain branching remains in `app.py`.

## Rollback and Fallback Guidance (If Regressions Appear)

### Immediate fallback strategy

1. Keep a legacy-route registration path available during migration:
   - `ROUTE_MODE=legacy|refactored|hybrid`
   - domain flags such as `ENABLE_BP_WORKFLOW`, `ENABLE_BP_BILLING`, etc.
2. If a regression appears in a domain, disable that domain's refactored blueprint flag and restart app.
3. Keep legacy handlers untouched until the corresponding domain passes smoke tests and a short canary window.

### Data safety fallback

- For sqlite environments, create per-wave DB snapshots.
- On data write regression, restore latest pre-wave snapshot and replay only validated actions if needed.
- Avoid schema migrations during this milestone to keep rollback simple.

### Operational fallback by symptom

- Auth/OAuth regression:
  - switch auth domain back to legacy route path immediately
  - keep login flow available for jury demo continuity
- Workflow execution regression:
  - route execution calls directly back to existing `execute_workflow` adapter path
- AI job regression:
  - keep `/api/ai/chat` synchronous fallback option returning non-async response or disable async job spawn temporarily
- Billing regression:
  - freeze admin approval actions and fallback to read-only wallet views while reverting billing blueprint

### Release gating before removing legacy fallback

- Two consecutive full smoke runs pass (clean DB and seeded DB).
- Critical flow demo script passes end-to-end.
- No unresolved route duplication warnings.
- Team signoff from backend + demo owner.

## Phase-Ready Architecture Checklist

- [ ] Baseline endpoint manifest exported from current app and committed.
- [ ] Critical flow smoke tests exist and pass on pre-refactor baseline.
- [ ] Dependency getter contract exists (no new module-level globals introduced).
- [ ] Service extraction completed for a domain while routes remain stable.
- [ ] Domain blueprint created and registered with unchanged URL/method contracts.
- [ ] Payload/status-code parity verified against baseline snapshots.
- [ ] Duplicate route behavior for that domain explicitly resolved and tested.
- [ ] Domain rollback flag tested (on/off) before moving to next domain.
- [ ] app.py no longer contains business SQL for completed domains.
- [ ] Final pass: app.py is composition-only and all legacy fallbacks are either removed with evidence or intentionally retained behind flags.
