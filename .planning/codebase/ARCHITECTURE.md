<!-- refreshed: 2026-07-08 -->
# Architecture

**Analysis Date:** 2026-07-08

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        Flask Web App (port 5000)                     │
│                             `app.py`                                 │
├───────────────┬───────────────┬───────────────┬─────────────────────┤
│  Auth/OAuth    │  Page/UI      │  Business API │  Admin/Ops routes   │
│ `routes/auth_  │ `routes/page_ │ `routes/sales_│ `routes/admin_*.py` │
│ routes.py`     │ routes.py`    │ inventory_    │ `routes/operations_ │
│                │               │ routes.py`... │ routes.py`          │
└───────┬────────┴───────┬───────┴───────┬───────┴──────────┬──────────┘
        │                │               │                  │
        ▼                ▼               ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Service Layer  `core/services/*.py`                    │
│  ai_chat_service, workflow_service, sales_service, wallet_service,   │
│  product_service, subscription_service, user_service, dl_client ...  │
└───────┬───────────────────────────────────────────┬───────────────┘
        │                                            │
        ▼                                            ▼
┌───────────────────────────────┐    ┌───────────────────────────────┐
│  Data Access `core/db/*.py`   │    │  External integrations         │
│  connection.py, user_repo.py, │    │  `core/google_integration.py`  │
│  activity_repo.py, workflow_  │    │  `core/make_integration.py`    │
│  repo.py, chat_repo.py        │    │  n8n via `routes/n8n_api.py`   │
└───────┬────────────────────────┘    └───────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────────┐
│  SQLite (dev) / Postgres (prod) via `core/database.py` shim         │
│  `database/group_project_ai_ml.db`, `migrations/` (Alembic-style)   │
└───────────────────────────────────────────────────────────────────┘

     Side services (separate Flask apps, run via threads/subprocess):
┌───────────────────────────┐   ┌────────────────────────────────────┐
│ DL Service (port 5001)    │   │ AI Agent Service (separate process) │
│ `dl_service/model_app.py` │   │ `ai_agent_service/src/server.py`    │
│ OCR/LSTM/forecast models  │   │ multi-agent chat/automation engine  │
└───────────────────────────┘   └────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| App factory | Builds Flask app, config, security (Talisman/CSRF), OAuth, blueprint registration | `app.py` |
| Route blueprints | HTTP request handling, auth checks, request/response shaping | `routes/*.py` |
| Service layer | Business logic, orchestrates repos and external integrations | `core/services/*.py` |
| DB repositories | SQL access per domain (users, activity, chat, workflow) | `core/db/*.py` |
| DB connection shim | Backward-compat wrapper around `core/db/connection.py` | `core/database.py` |
| Auth manager | Login/session/password logic, used by Flask-Login callbacks | `core/auth.py` |
| Automation engine | Workflow trigger/automation execution | `core/automation_engine.py`, `core/workflow_engine.py` |
| Agent middleware | Bridges AI agent actions into app-level operations | `core/agent_middleware.py` |
| Google integration | Drive/Sheets/Docs/Gmail/Analytics via OAuth | `core/google_integration.py` |
| Make.com integration | Webhook-based automation to Make.com | `core/make_integration.py` |
| n8n integration | REST endpoints n8n calls into the app (CSRF-exempt) | `routes/n8n_api.py` |
| DL Service app | Standalone Flask app for OCR/LSTM/invoice forecasting models | `dl_service/model_app.py` |
| DL API routes | Model 1/2, OCR, history endpoints | `dl_service/api/*.py` |
| DL service layer | Model loading, OCR pipeline, forecasting, layout detection | `dl_service/services/*.py` |
| AI Agent Service | Independent multi-agent server (manager/coder/researcher/vision agents) | `ai_agent_service/src/server.py`, `ai_agent_service/src/agents/*.py` |

## Pattern Overview

**Overall:** Layered monolith (Flask "Blueprints → Services → Repositories → DB") with two loosely-coupled sibling services (DL model service, AI agent service) that the main app talks to over HTTP/thread boundaries rather than in-process calls.

**Key Characteristics:**
- Application factory pattern (`create_app()` in `app.py`) — no module-level app instance is used in production paths.
- Flask extensions (`login_manager`, `csrf`, `limiter`, `db_manager`) centralized in `core/extensions.py` and attached to `flask_app.extensions[...]` for blueprint access, avoiding circular imports.
- Business logic isolated in `core/services/`, never directly in route handlers (though some route files still contain logic — see CONCERNS).
- The DL service and AI agent service are separate Flask/Python processes with their own `api/`, `services/`, `models/`, `database/` subtrees, mirroring the main app's layering internally.
- The main app starts the DL service in a background thread (`run_dl_service()` in `app.py`, port 5001) and checks for n8n reachability (`run_n8n()`), but does not launch `ai_agent_service` automatically — it is run separately (`ai_agent_service/main.py` / `launch_demo.py`).

## Layers

**Routes (`routes/`):**
- Purpose: HTTP endpoint definitions, request validation, session/auth checks, CSRF handling
- Location: `routes/*.py` (auth, main, page, sales, workspace, wallet, google, admin_user, admin_subscription, admin_warehouse, operations, ai, inventory, workflow, dl, n8n_api)
- Contains: Flask Blueprints registered in `app.py`
- Depends on: `core/services/*`, `core/auth.py`, `flask_login.current_user`
- Used by: Flask app dispatch

**Services (`core/services/`):**
- Purpose: Business logic, cross-repo orchestration, validation rules
- Location: `core/services/*.py`
- Contains: `ai_chat_service.py`, `analytics_service.py`, `customer_service.py`, `dl_client.py` (HTTP client to DL service), `inventory_tx_service.py`, `operations_service.py`, `product_service.py`, `sales_service.py`, `service_errors.py`, `subscription_service.py`, `user_service.py`, `wallet_service.py`, `workflow_service.py`, `workspace_service.py`
- Depends on: `core/db/*`, `core/models.py`
- Used by: `routes/*.py`

**Data access (`core/db/`):**
- Purpose: Raw SQL/repo pattern per domain
- Location: `core/db/connection.py`, `user_repo.py`, `activity_repo.py`, `chat_repo.py`, `workflow_repo.py`
- Depends on: SQLite/Postgres via `Database` class in `connection.py`
- Used by: `core/services/*`

**Core cross-cutting (`core/`):**
- Purpose: Config, security, logging, auth, integrations shared across the app
- Location: `core/config.py`, `core/security.py`, `core/logger.py`, `core/auth.py`, `core/extensions.py`, `core/helpers.py`, `core/utils.py`, `core/excel_parser.py`, `core/google_integration.py`, `core/make_integration.py`, `core/automation_engine.py`, `core/workflow_engine.py`, `core/agent_middleware.py`

**DL Service (`dl_service/`):**
- Purpose: Standalone Flask app serving OCR, LSTM forecasting, and invoice extraction models
- Location: `dl_service/model_app.py` (entry), `dl_service/api/*.py` (routes), `dl_service/services/*.py`, `dl_service/models/*` (model code + saved weights in `dl_service/saved_models/`), `dl_service/utils/`, `dl_service/database/`
- Depends on: TensorFlow/Keras, VietOCR/CPT OCR models
- Used by: Main app via `core/services/dl_client.py` (HTTP calls to port 5001), and directly via `routes/dl_routes.py`

**AI Agent Service (`ai_agent_service/`):**
- Purpose: Multi-agent orchestration (manager/coder/researcher/vision agents), separate from the main Flask request cycle
- Location: `ai_agent_service/src/server.py` (entry), `ai_agent_service/src/agents/*.py`, `ai_agent_service/src/core/*.py` (engine, memory, tools, prompts, integrations)
- Depends on: LLM APIs (via `core/integrations.py`, `core/saas_api.py`)
- Used by: Main app's `core/services/ai_chat_service.py` and `core/agent_middleware.py` bridge into it over HTTP/process boundary

## Data Flow

### Primary Request Path (web UI/API)

1. Request hits a registered blueprint route, e.g. `routes/sales_routes.py` (`app.py:register_blueprint`)
2. Route handler checks auth via `flask_login.current_user` / `core/auth.py:AuthManager`
3. Route calls into a service, e.g. `core/services/sales_service.py`
4. Service calls a repo in `core/db/*.py`, which executes SQL through `core/db/connection.py:Database`
5. Result flows back up: repo → service → route → `jsonify(...)` or rendered template (`ui/templates/`)

### DL Model Inference Path

1. Route `routes/dl_routes.py` receives request (e.g. OCR upload) or `core/services/dl_client.py` makes an HTTP call to `http://localhost:5001`
2. DL service app (`dl_service/model_app.py`) dispatches to `dl_service/api/ocr_routes.py` / `model1_routes.py` / `model2_routes.py`
3. API route calls `dl_service/services/ocr_service.py`, `forecast_service.py`, `layout_service.py`, or `invoice_service.py`
4. Service loads models via `dl_service/services/model_loader.py` from `dl_service/saved_models/`
5. Result returned as JSON to caller

### Workflow/Automation Path

1. `core/automation_engine.py` and `core/workflow_engine.py` orchestrate multi-step automations
2. Triggered via `routes/workflow_routes.py` or `routes/n8n_api.py` (external n8n webhooks, CSRF-exempt)
3. Persist workflow state via `core/db/workflow_repo.py`
4. May call out to `core/google_integration.py` or `core/make_integration.py` for external actions

**State Management:**
- Server-side session (Flask-Login) with SQL-backed user store (`core/models.py:User`, `core/db/user_repo.py`)
- Background job files persisted as JSON in `jobs/` (one file per job UUID) rather than in the SQL database — used for async/long-running task tracking
- No client-side global state framework detected; server-rendered templates plus fetch-based JS in `static/js/`

## Key Abstractions

**Blueprint (Flask):**
- Purpose: Groups related routes under a URL prefix
- Examples: `routes/auth_routes.py` (`auth_bp`), `routes/dl_routes.py` (`dl_bp`)
- Pattern: Each blueprint module exports a `Blueprint` instance; `app.py` imports and registers all of them in `create_app()`

**Service class/module:**
- Purpose: Encapsulates one business domain's logic
- Examples: `core/services/wallet_service.py`, `core/services/subscription_service.py`
- Pattern: Function or class-based modules called from routes, one file per domain

**Repository (`*_repo.py`):**
- Purpose: Encapsulates SQL statements for one entity/domain
- Examples: `core/db/user_repo.py`, `core/db/workflow_repo.py`
- Pattern: Thin wrapper functions/classes around `core/db/connection.py:Database`

**Extensions registry:**
- Purpose: Avoids circular imports; singletons initialized once and attached to `flask_app.extensions`
- Location: `core/extensions.py` (login_manager, csrf, limiter, db_manager)
- Pattern: Imported in `app.py`, `.init_app(flask_app)` called inside `create_app()`

## Entry Points

**Main web app:**
- Location: `app.py`
- Triggers: `python app.py` (dev), likely a WSGI server in production
- Responsibilities: Builds Flask app via `create_app()`, registers all blueprints, starts DL service thread, checks n8n

**DL Service (standalone):**
- Location: `dl_service/model_app.py` (also runnable via `run_dl_service.py` at repo root)
- Triggers: `python run_dl_service.py` or `python dl_service/model_app.py`, or spawned as a background thread by `app.py:run_dl_service()`
- Responsibilities: Serves OCR/LSTM/forecast model endpoints on port 5001

**AI Agent Service (standalone):**
- Location: `ai_agent_service/src/server.py`, launched via `ai_agent_service/main.py`
- Triggers: `python ai_agent_service/main.py`
- Responsibilities: Runs manager/coder/researcher/vision agent orchestration independent of the Flask request cycle

## Architectural Constraints

- **Threading:** Main app runs DL service in a background `threading.Thread` (daemon) inside the same process (`app.py:run_dl_service`), and n8n reachability check in another daemon thread. This means DL service inference is not isolated from the main app's Python process/GIL.
- **Global state:** Module-level singleton `config = Config()` in `app.py`; `core/extensions.py` holds process-wide singletons (`login_manager`, `csrf`, `limiter`, `db_manager`) attached to Flask's `extensions` dict rather than passed explicitly.
- **Cross-service coupling:** Main app and DL service communicate over HTTP to `localhost:5001` (`core/services/dl_client.py`) even though DL service may run in-process (thread) — effectively a loopback HTTP call rather than a function call, adding latency/failure-mode surface.
- **File-based job queue:** `jobs/*.json` acts as an ad hoc persistence layer for async task state outside the main SQL database — not transactional with the rest of app state.

## Anti-Patterns

### Business logic leaking into route handlers

**What happens:** Some route files (e.g. `routes/n8n_api.py` at 531 lines, `routes/main_routes.py` at 321 lines) contain substantial logic beyond request parsing/response shaping.
**Why it's wrong:** Makes routes hard to test in isolation and duplicates logic that should live in `core/services/`.
**Do this instead:** Extract non-HTTP logic into a corresponding `core/services/*.py` module, following the pattern already used by `sales_routes.py` → `sales_service.py`.

### Loopback HTTP between co-located processes

**What happens:** `core/services/dl_client.py` calls the DL service over HTTP to `localhost:5001` even when it's running in the same process via a background thread.
**Why it's wrong:** Adds unnecessary network round-trip and failure modes (connection refused during startup race) for what could be a direct Python call when co-hosted.
**Do this instead:** If DL service must remain a separate deployable, keep the HTTP client but consider a startup health check before serving requests; if it's meant to run in-process, expose a direct import path instead of forcing an HTTP hop.

## Error Handling

**Strategy:** Centralized Flask error handlers registered in `create_app()`, differentiating JSON API responses (`/api/*` paths) from HTML flash/redirect flows.

**Patterns:**
- `@flask_app.errorhandler(CSRFError)` — returns 400/401 JSON for `/api/*`, flash+redirect otherwise (`app.py`)
- `@flask_app.errorhandler(Exception)` — catches all uncaught exceptions, returns sanitized JSON via `core/security.py:safe_api_error` for `/api/*` paths to avoid leaking internals, re-raises for non-API HTTP exceptions
- Service-layer errors defined in `core/services/service_errors.py`

## Cross-Cutting Concerns

**Logging:** `core/logger.py:get_logger(__name__)` used throughout; DL service has its own `dl_service/utils/logger.py` with `setup_logging()`
**Validation:** CSRF via `flask_wtf.csrf`, per-route validation typically inline in route handlers; `MAX_CONTENT_LENGTH` enforced globally
**Authentication:** `flask_login` + `core/auth.py:AuthManager` + Google OAuth via `authlib` (`core/google_integration.py`); session cookies configured for secure/HTTPOnly/SameSite in `app.py`
**Security headers:** `flask_talisman.Talisman` configures CSP, HSTS, frame options in `app.py`
**Rate limiting:** `flask_limiter` (`core/extensions.py:limiter`), default limits set in `app.py` (`RATELIMIT_DEFAULT_LIMITS`)

---

*Architecture analysis: 2026-07-08*
