<!-- refreshed: 2026-05-16 -->
# Architecture

**Analysis Date:** 2026-05-16

## System Overview

```text
┌───────────────────────────────────────────────────────────────────────┐
│                    Browser / API Clients                               │
└──────────────────────────────┬────────────────────────────────────────┘
                               │ HTTP
                               ▼
┌───────────────────────────────────────────────────────────────────────┐
│              Main Flask App   (port 5000)                              │
│              `app.py`  ·  `routes/`  ·  `ui/templates/`              │
│                                                                        │
│  Blueprints registered via create_app():                               │
│  auth_bp · page_bp · main_bp · sales_bp · workspace_bp · wallet_bp   │
│  google_bp · admin_user_bp · admin_sub_bp · operations_bp             │
│  inventory_bp · workflow_bp · ai_bp · dl_bp                           │
└─────────┬──────────────────────────┬──────────────────────────────────┘
          │ direct import (use_local) │ HTTP fallback
          ▼                          ▼
┌─────────────────────┐   ┌──────────────────────────────────────────┐
│  Deep Learning      │   │  AI Chat / HuggingFace Inference          │
│  Service (port 5001)│   │  (external, called from ai_routes.py)    │
│  `dl_service/`      │   │  env: HF_BASE_URL, HF_TOKEN              │
│  model_app.py       │   └──────────────────────────────────────────┘
│  YOLO + LSTM + OCR  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Database Layer                                    │
│   SQLite `group_project_ai_ml.db`  OR  PostgreSQL (POSTGRES_URL)    │
│   `core/database.py`  —  Database class + PGShimCursor              │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Key Files |
|-----------|----------------|-----------|
| Application factory | App creation, extension wiring, blueprint registration | `app.py` |
| Extensions singleton | Flask extension instances (LoginManager, CSRFProtect, Limiter, Database) shared without circular imports | `core/extensions.py` |
| Route blueprints | HTTP request/response handling, delegating to services | `routes/*.py` |
| Service layer | Domain business logic, DB queries | `core/services/*.py` |
| Database abstraction | SQLite/PostgreSQL compatibility shim, schema init | `core/database.py` |
| AuthManager | User credential verification, registration, password hashing | `core/auth.py` |
| AgentMiddleware | AI response parsing, JSON extraction, workflow action dispatch | `core/agent_middleware.py` |
| AutomationEngine | Background scheduler thread for recurring automation jobs | `core/automation_engine.py` |
| WorkflowEngine | DAG-based multi-node workflow execution (topological sort) | `core/workflow_engine.py` |
| DLClient | Proxy to DL service — supports local direct-import or remote HTTP | `core/services/dl_client.py` |
| Google integration | Drive, Sheets, Gmail, Analytics API wrappers | `core/google_integration.py` |
| DL service app | Self-contained Flask app (port 5001): YOLO layout detector + LSTM + OCR | `dl_service/model_app.py` |
| DL service APIs | Blueprint routes for detect, forecast, OCR, history | `dl_service/api/*.py` |
| DL services | Model loading, invoice processing, forecast, OCR | `dl_service/services/*.py` |
| Jinja2 templates | Server-side rendered UI pages | `ui/templates/*.html` |

## Pattern Overview

**Overall:** Application factory + Blueprint decomposition monolith with a detached deep-learning microservice.

**Key Characteristics:**
- `create_app()` in `app.py` is the sole place where Flask extensions are bound to the app instance, avoiding circular imports.
- Service classes and domain dependencies are stored in `flask_app.extensions` dict and retrieved via `current_app.extensions['key']` inside blueprints.
- The DL service runs either as a separate process on port 5001 or is called directly via local Python import (`DLClient(use_local=True)`), determined at runtime.
- Async AI tasks use a file-based job store (`jobs/*.json`) with a background thread rather than a task queue.

## Layers

**Presentation Layer:**
- Purpose: Serve HTML pages via Jinja2 templates and inject CSRF tokens, project config, and user session via context processors.
- Location: `ui/templates/` (templates), `static/css/`, `static/js/`
- Contains: Per-feature HTML templates, `base.html` layout, `components/` partials
- Depends on: Authentication layer (Flask-Login current_user), route layer
- Used by: Browsers

**Routing Layer:**
- Purpose: Accept HTTP requests, validate inputs, call service layer, return JSON or rendered templates.
- Location: `routes/`
- Contains: 14 Flask Blueprint modules (`auth_routes.py`, `main_routes.py`, `ai_routes.py`, `dl_routes.py`, `workflow_routes.py`, `sales_routes.py`, `wallet_routes.py`, `google_routes.py`, `inventory_routes.py`, `operations_routes.py`, `workspace_routes.py`, `page_routes.py`, `admin_user_routes.py`, `admin_subscription_routes.py`)
- Depends on: Service layer, core extensions
- Used by: Browser, API clients

**Service Layer:**
- Purpose: Encapsulate domain logic away from HTTP concerns.
- Location: `core/services/`
- Contains: `ai_chat_service.py`, `analytics_service.py`, `customer_service.py`, `dl_client.py`, `inventory_tx_service.py`, `operations_service.py`, `product_service.py`, `sales_service.py`, `service_errors.py`, `subscription_service.py`, `user_service.py`, `wallet_service.py`, `workflow_service.py`, `workspace_service.py`
- Depends on: Database layer
- Used by: Routing layer

**Core Business Logic:**
- Purpose: Cross-cutting application services (auth, workflows, automation, AI middleware, Google integrations).
- Location: `core/`
- Contains: `auth.py`, `workflow_engine.py`, `automation_engine.py`, `agent_middleware.py`, `google_integration.py`, `make_integration.py`, `helpers.py`, `utils.py`, `models.py`
- Depends on: Database layer, external APIs
- Used by: Routing layer, service layer

**Database Layer:**
- Purpose: Provide a unified cursor-based interface over SQLite or PostgreSQL.
- Location: `core/database.py`
- Contains: `Database` class, `PGShimCursor`, `PGShimConnection`, schema init via `init_database()`
- Depends on: `sqlite3` (stdlib) or `psycopg2` (PostgreSQL)
- Used by: All layers

**Deep Learning Service:**
- Purpose: Serve YOLO-based invoice layout detection, LSTM quantity forecasting, and OCR as REST endpoints.
- Location: `dl_service/`
- Contains: `model_app.py` (Flask entry), `api/` (4 blueprints), `services/` (model_loader, invoice_service, forecast_service, layout_service, ocr_service), `models/` (YOLO weights, VietOCR, LSTM checkpoints), `utils/`
- Depends on: TensorFlow, PyTorch, ultralytics, VietOCR
- Used by: Main app via `DLClient`

## Data Flow

### Web Request (authenticated page or API call)

1. Browser sends request → Werkzeug/ProxyFix → Flask router (`app.py` via blueprints in `routes/`)
2. `@login_required` decorator checks Flask-Login session; unauthorized → redirect to `auth.signin` or 401 JSON
3. Blueprint handler calls service function in `core/services/*.py`
4. Service function calls `db_manager.get_connection()` → executes SQL → returns data dict
5. Blueprint handler returns `jsonify(...)` or `render_template(...)` with template in `ui/templates/`

### AI Chat Request (async job)

1. POST `/api/ai/chat` → `routes/ai_routes.py:api_ai_chat()`
2. Creates `job_id`, writes `jobs/{job_id}.json` with status `processing`
3. Spawns background thread `background_ai_task(job_id, user_id, message)`
4. Thread calls `AgentMiddleware.get_system_context()` → HTTP POST to `HF_BASE_URL/chat` with `HF_TOKEN`
5. AI response parsed by `AgentMiddleware.process_ai_response()` for workflow action JSON
6. Result written to `jobs/{job_id}.json` with status `done`
7. Client polls GET `/api/ai/job/{job_id}` → reads job file → returns result

### Invoice Processing (DL pipeline)

1. POST `/api/dl/detect` → `routes/dl_routes.py:api_dl_detect()`
2. `DLClient().detect_invoice(file_bytes=...)` — if `use_local=True`, directly calls `dl_service/services/invoice_service.py:process_invoice_image()`
3. YOLO layout detector (`dl_service/services/layout_service.py`) segments invoice image
4. OCR pipeline extracts text per segment (`dl_service/services/ocr_service.py`)
5. Result dict returned to route handler → JSON response

### Workflow Execution

1. POST `/api/workflows/{id}/execute` → `routes/workflow_routes.py`
2. Workflow JSON loaded from DB → passed to `core/workflow_engine.execute_workflow(workflow_data)`
3. `execute_workflow()`: builds adjacency list → Kahn's topological sort → iterates nodes in dependency order
4. Per node: `resolve_template()` substitutes `{{nodeId.field}}` references from prior node outputs
5. Node dispatches to: Google Sheets/Docs/Gmail (`core/google_integration.py`), webhooks (`core/make_integration.py`), or DL service (`DLClient`)
6. Each node result stored in `context[node_id]` for downstream nodes

**State Management:**
- Web session state: Flask server-side sessions with `PERMANENT_SESSION_LIFETIME=7 days`
- User identity: Flask-Login `current_user` proxy backed by `AuthManager.get_user_by_id()`
- Async job state: File-based JSON in `jobs/` directory (not Redis/Celery)
- Shared application services: stored in `flask_app.extensions` dict, retrieved via `current_app.extensions`

## Key Abstractions

**Database:**
- Purpose: Unified connection interface over SQLite and PostgreSQL
- Location: `core/database.py`
- Pattern: `Database.get_connection()` returns either `sqlite3.Connection` or `PGShimConnection` (wraps psycopg2). `PGShimCursor` rewrites `?` → `%s` and injects `RETURNING id` on INSERTs for PostgreSQL lastrowid compatibility. Schema initialized via `init_database()` (SQLite only; PostgreSQL uses migration scripts in `scripts/`).

**DLClient:**
- Purpose: Decouple main app from whether DL service is local or remote
- Location: `core/services/dl_client.py`
- Pattern: Constructor param `use_local=True` controls dispatch. Local path imports `dl_service/services/*.py` directly. Remote path POSTs to `DL_SERVICE_URL` (default `http://localhost:5001`). Methods: `detect_invoice()`, `forecast_quantity()`, `run_ocr()`.

**WorkflowEngine:**
- Purpose: Execute user-defined multi-step automation pipelines as DAGs
- Location: `core/workflow_engine.py`
- Pattern: `execute_workflow(workflow_data)` → Kahn's algorithm on `nodes` + `edges` JSON. Node types dispatch to Google APIs, webhooks, DL models. `resolve_template()` uses `eval()` on `{{nodeId.path}}` expressions to pass data between nodes.

**AuthManager:**
- Purpose: Centralise all credential and user lifecycle operations
- Location: `core/auth.py`
- Pattern: Constructor-injected `Database`. Passwords hashed with SHA-256 (not bcrypt despite bcrypt in requirements). Methods: `verify_user()`, `register_user()`, `get_user_by_id()`, `get_user_by_email()`.

**AutomationEngine:**
- Purpose: Background scheduler for time-triggered workflows
- Location: `core/automation_engine.py`
- Pattern: Daemon thread polls `se_automations` table every 60 seconds. Registered as `flask_app.extensions['automation_engine']`. Must be started explicitly via `.start()`.

**AgentMiddleware:**
- Purpose: Extract and dispatch workflow action JSON from LLM free-text responses
- Location: `core/agent_middleware.py`
- Pattern: Scans AI response for markdown-fenced or inline JSON with `action: create_workflow`. Passes to DB. Falls back to raw text display on parse failure.

## Entry Points

**Main Flask App:**
- Location: `app.py` — `create_app()` factory + module-level `app = create_app()`
- Triggers: `python app.py` (development) or WSGI server pointing to `app:app`
- Responsibilities: Extension init, OAuth config, Talisman security headers, CSRF, rate limiting, all blueprint registration

**Deep Learning Service:**
- Location: `dl_service/model_app.py` (standalone Flask)
- Triggers: `python run_dl_service.py` (standalone) OR spawned as a thread inside `app.py:run_dl_service()` when main app starts
- Responsibilities: Model loading (YOLO + LSTM on startup), OCR routes, forecast routes, invoice detection

**DL Service Launcher:**
- Location: `run_dl_service.py`
- Triggers: `python run_dl_service.py`
- Responsibilities: Adds `dl_service/` to `sys.path`, imports and runs `model_app.app` on port 5001

## Architectural Constraints

- **Threading:** Single-threaded Flask event loop for web requests. AutomationEngine uses one daemon thread. AI background jobs each spin a new thread; no pool is managed. DL service is optionally threaded inside main app.
- **Global state:** `db_manager` singleton created at module import time in `core/extensions.py` (line 36). `config = Config()` module-level in `app.py`. DL service keeps global `lstm_model` and `layout_ready` in `dl_service/services/model_loader.py`.
- **Circular imports:** Blueprints in `routes/` use `_app_module()` lazy import helpers (`import app as app_module`) to access `app.db` and `app.workflow_service` — indicates incomplete refactor; some globals still live on the module-level `app` object.
- **Password hashing:** `AuthManager.hash_password()` uses SHA-256 only — bcrypt listed in requirements but not invoked.
- **Workflow template eval:** `core/workflow_engine.py:resolve_template()` uses `eval()` on user-supplied template strings — security risk if workflow data is externally sourced.

## Anti-Patterns

### Lazy `import app` inside blueprints

**What happens:** `routes/workflow_routes.py` and `routes/ai_routes.py` call `_app_module()` which does `import app` at request time to read `app.db` and `app.workflow_service`.
**Why it's wrong:** Couples blueprints to the module-level `app` object rather than `current_app.extensions`, breaking the application factory pattern and preventing testing with multiple app instances.
**Do this instead:** Store services in `flask_app.extensions` inside `create_app()` and retrieve via `current_app.extensions['key']` — already done correctly for `auth_manager`, `agent_middleware`, `automation_engine`.

### SHA-256 password hashing

**What happens:** `core/auth.py:AuthManager.hash_password()` uses `hashlib.sha256`.
**Why it's wrong:** SHA-256 is a fast hash — vulnerable to brute force. bcrypt is in requirements but unused.
**Do this instead:** Replace with `passlib.hash.bcrypt.hash(password)` / `passlib.hash.bcrypt.verify(password, stored)`.

### eval() in workflow template resolver

**What happens:** `core/workflow_engine.py:resolve_template()` calls `eval(expr, {"ctx": context})` on workflow node template strings.
**Why it's wrong:** Arbitrary code execution if attacker controls workflow JSON.
**Do this instead:** Implement a safe path traversal function that parses `nodeId.field[0]` expressions without eval.

## Error Handling

**Strategy:** Per-layer try/except with console logging. No centralised error middleware beyond Flask's built-in `errorhandler` for CSRF (400) and unauthorized (401).

**Patterns:**
- Route handlers: `try/except Exception as e: return jsonify({'success': False, 'message': str(e)}), 500`
- Database layer: exceptions propagate to caller; connections always closed in `finally` blocks
- DLClient: catches `requests.exceptions.RequestException`, returns `{"error": str(e), "status": "failed"}`
- Auth routes: catch generic `Exception`, flash error message, render form again
- CSRF errors: `@flask_app.errorhandler(CSRFError)` — returns 400 JSON for API, redirect for browser

## Cross-Cutting Concerns

**Logging:** Mix of `print()` statements (most code) and no structured logger in the main app. `dl_service/utils/logger.py` provides a `get_logger(__name__)` utility used within DL service only.
**Validation:** Ad-hoc in route handlers — check required fields in request JSON/form, return 400 with message. `dl_service/utils/validators.py` provides file validation helpers.
**Authentication:** Flask-Login session cookies + `@login_required` decorator on all protected routes. Google OAuth via authlib registered as `app.extensions['google']`.
**Rate Limiting:** Flask-Limiter applied per-endpoint (e.g., `@limiter.limit("5 per minute")` on signin). Disabled globally in development via `RATELIMIT_ENABLED=False`.
**CSRF:** Flask-WTF CSRFProtect on all state-changing routes. API endpoints that accept JSON from JS use `@csrf.exempt` or rely on CSRF token in headers.
**Security headers:** Flask-Talisman applies HSTS, X-Frame-Options DENY, X-Content-Type-Options, permissive CSP (unsafe-inline/eval allowed — development config).

---

*Architecture analysis: 2026-05-16*
