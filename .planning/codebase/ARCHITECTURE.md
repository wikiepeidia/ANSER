<!-- refreshed: 2026-06-08 -->
# Architecture

**Analysis Date:** 2026-06-08

## System Overview

```text
Browser / Server-rendered UI
`ui/templates/`, `static/css/`, `static/js/`
        |
        v
Main Flask Application
`app.py`
        |
        +-- Flask extension singletons
        |   `core/extensions.py`
        |
        +-- Domain route Blueprints
        |   `routes/*.py`
        |
        +-- Business and orchestration services
        |   `core/services/*.py`, `core/workflow_engine.py`,
        |   `core/automation_engine.py`, `core/agent_middleware.py`
        |
        +-- Persistence facade and repositories
        |   `core/db/connection.py`, `core/db/*_repo.py`,
        |   `migrations/`
        |
        +-- External/service adapters
            `core/google_integration.py`, `core/make_integration.py`,
            `core/services/dl_client.py`, `routes/ai_routes.py`
                |
                +-- Deep Learning Flask service
                |   `dl_service/model_app.py`, `dl_service/api/`,
                |   `dl_service/services/`, `dl_service/models/`
                |
                +-- AI Agent FastAPI service
                    `ai_agent_service/src/server.py`,
                    `ai_agent_service/src/agents/`,
                    `ai_agent_service/src/core/`
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Main app factory | Creates the Flask app, configures security/session/CSRF/login, binds dependencies, and registers route blueprints. | `app.py` |
| Extension singletons | Provides app-independent `login_manager`, `csrf`, `limiter`, and `db_manager` objects for import from routes without constructing the app. | `core/extensions.py` |
| Route layer | Owns HTTP endpoints, login/role checks, request parsing, response shaping, and blueprint definitions. | `routes/*.py` |
| Page routes | Maps page URLs to Jinja templates and guards role-specific pages. | `routes/page_routes.py` |
| Domain services | Owns product, customer, inventory, workflow, AI chat, wallet, operations, user, subscription, and sales business operations. | `core/services/*.py` |
| Service errors | Provides typed service exceptions for route-to-service contracts. | `core/services/service_errors.py` |
| Database facade | Creates SQLite/PostgreSQL-compatible connections, initializes local SQLite schema, and delegates selected calls to repositories. | `core/db/connection.py` |
| Repositories | Encapsulate row-level persistence for users, activity, AI chat, and workflows. | `core/db/*_repo.py` |
| Auth manager | Handles password verification, registration, user lookup, and auth-related decorators. | `core/auth.py` |
| User model | Provides the Flask-Login `UserMixin` user object. | `core/models.py` |
| Workflow engine | Executes workflow DAGs with topological sorting and node handlers for Google, webhooks, notifications, filters, OCR, and forecast nodes. | `core/workflow_engine.py` |
| Agent middleware | Builds AI context from database schema and converts AI JSON actions into application workflow records. | `core/agent_middleware.py` |
| Automation engine | Runs scheduled and stock-triggered automation checks on a background thread. | `core/automation_engine.py` |
| DL adapter | Calls `dl_service` locally through imports or remotely through HTTP endpoints. | `core/services/dl_client.py` |
| DL Flask service | Hosts OCR, invoice detection, forecasting, history, model startup, and local invoice persistence. | `dl_service/model_app.py` |
| DL service layer | Processes images, OCR fallback chains, layout detection, invoice parsing, and LSTM forecasting. | `dl_service/services/*.py` |
| AI Agent service | Hosts FastAPI `/chat`, `/upload`, and `/ocr` endpoints backed by manager/coder/vision agents and RAG memory. | `ai_agent_service/src/server.py` |
| Jinja UI | Provides server-rendered pages, shared base layout, sidebar, and chat widget. | `ui/templates/` |
| Static UI assets | Provides per-page CSS/JS, shared theme scripts, chat scripts, and favicon assets. | `static/` |
| Alembic migrations | Manages PostgreSQL schema with raw SQL migration scripts. | `migrations/env.py`, `migrations/versions/001_initial_schema.py` |
| GSD workflow tooling | Provides local agent/workflow skills and generated planning context consumed by GSD commands. | `.codex/skills/`, `.planning/`, `.github/skills/` |

## Pattern Overview

**Overall:** Flask modular monolith with local/remote AI and deep-learning service boundaries.

**Key Characteristics:**
- Use `app.py` as the composition root. `create_app()` builds the app at `app.py:60`, stores dependencies in `flask_app.extensions` at `app.py:133`, and registers Blueprints at `app.py:203`.
- Use `core/extensions.py` for extension singletons. `core/extensions.py:3` documents the init-app pattern and `core/extensions.py:36` constructs the shared `Database` facade.
- Use `routes/*.py` for HTTP behavior. Route modules define `Blueprint(...)`, `@...route(...)`, `@login_required`, request parsing, and `jsonify(...)`.
- Use `core/services/*.py` for domain logic. Prefer plain values, explicit `db_conn` arguments, and typed service exceptions for new service work, as shown in `core/services/inventory_tx_service.py` and `core/services/workflow_service.py`.
- Use `core/db/connection.py` for database connections and schema compatibility. `core/db/connection.py:24` converts SQLite `?` placeholders for PostgreSQL, and `core/db/connection.py:138` selects SQLite or PostgreSQL connections.
- Use `ui/templates/` and `static/` for the frontend. `app.py:64` sets `template_folder='ui/templates'`, and `ui/templates/base.html` loads shared CSS/JS from `static/`.
- Treat `dl_service/` and `ai_agent_service/` as separate service subtrees. Main app calls them through `core/services/dl_client.py` and `routes/ai_routes.py`, not by mixing their internals into route handlers.

## Layers

**Presentation Layer:**
- Purpose: Render HTML pages and run browser-side interactions.
- Location: `ui/templates/`, `static/css/`, `static/js/`, `static/img/`
- Contains: Jinja pages, shared components, page-specific CSS/JS, theme bootstrap, chat widget scripts.
- Depends on: Flask `url_for('static', ...)`, route endpoints in `routes/*.py`, CSRF token injected by `app.py:184`.
- Used by: Browser sessions served by `routes/page_routes.py`.

**Main Flask Composition Layer:**
- Purpose: Build the runtime app and bind global Flask services to an app instance.
- Location: `app.py`, `core/extensions.py`
- Contains: `create_app()`, Talisman configuration, Flask-Login callbacks, CSRF and error handlers, dependency instances, blueprint registration.
- Depends on: `core.config.Config`, `core.extensions`, `core.auth.AuthManager`, `core.automation_engine.AutomationEngine`, `core.agent_middleware.AgentMiddleware`, `routes/*.py`.
- Used by: `python app.py`, pytest fixtures in `tests/conftest.py`, deployment imports of `app.app`.

**Route Layer:**
- Purpose: Own request/response concerns and delegate domain operations.
- Location: `routes/`
- Contains: Blueprint modules such as `routes/main_routes.py`, `routes/inventory_routes.py`, `routes/workflow_routes.py`, `routes/ai_routes.py`, and `routes/dl_routes.py`.
- Depends on: Flask, Flask-Login, `core.extensions.db_manager`, `core.services.*`, and selected app-scoped dependencies in `current_app.extensions`.
- Used by: `app.py` blueprint registration.

**Domain Service Layer:**
- Purpose: Own business rules, validation, transaction behavior, and orchestration below HTTP.
- Location: `core/services/`, `core/workflow_engine.py`, `core/automation_engine.py`, `core/agent_middleware.py`, `core/auth.py`
- Contains: Service functions, typed exceptions, workflow execution, AI response processing, auth operations, background automation.
- Depends on: Database connections, `core.google_integration`, `core.make_integration`, `core.services.dl_client`, and domain helper modules.
- Used by: Route modules and selected background workers.

**Persistence Layer:**
- Purpose: Provide storage access for users, workspaces, inventory, sales, subscriptions, workflows, AI chat history, and activity logs.
- Location: `core/db/connection.py`, `core/db/*_repo.py`, `migrations/`
- Contains: `Database`, `PGShimConnection`, `PGShimCursor`, SQLite schema bootstrap, repository classes, Alembic raw SQL migrations.
- Depends on: `core.config.Config`, SQLite, optional psycopg2/PostgreSQL, Alembic for migrations.
- Used by: `core/extensions.db_manager`, services, auth manager, route modules, tests.

**External Integration Layer:**
- Purpose: Encapsulate Google APIs, webhooks, DL access, AI agent access, and analytics.
- Location: `core/google_integration.py`, `core/make_integration.py`, `core/services/dl_client.py`, `core/services/analytics_service.py`, `routes/ai_routes.py`
- Contains: Google service construction, Drive/Sheets/Docs/Gmail calls, webhook POST/GET, DL HTTP/local adapter, AI chat background task.
- Depends on: Environment variables, token data, `requests`, Google client libraries, optional external services.
- Used by: Workflow engine, route modules, AI chat route, DL proxy routes.

**Deep Learning Service Layer:**
- Purpose: Run OCR, invoice extraction, layout detection, forecast APIs, and model state.
- Location: `dl_service/`
- Contains: Flask app in `dl_service/model_app.py`, API blueprints in `dl_service/api/`, model/service code in `dl_service/services/` and `dl_service/models/`, local invoice database in `dl_service/utils/database.py`.
- Depends on: OpenCV, TensorFlow/Keras, PyTorch/TorchVision, PaddleOCR/EasyOCR/Tesseract, image datasets, model weights.
- Used by: `core/services/dl_client.py`, direct service execution, workflow OCR/forecast nodes.

**AI Agent Service Layer:**
- Purpose: Run FastAPI chat, upload, OCR, RAG, and multi-agent reasoning endpoints.
- Location: `ai_agent_service/src/`
- Contains: FastAPI app in `ai_agent_service/src/server.py`, agents in `ai_agent_service/src/agents/`, engine/memory/RAG/integration code in `ai_agent_service/src/core/`.
- Depends on: vLLM, transformers, Qwen models, FastAPI, SQLAlchemy, ChromaDB, vector data.
- Used by: `routes/ai_routes.py` through `HF_BASE_URL` and by `dl_service/services/ocr_service.py` through the Brain VLM fallback.

## Data Flow

### Primary Request Path

1. Flask constructs the app with `create_app()` and binds configuration, CSRF, login, and dependencies (`app.py:60`, `app.py:128`).
2. `app.py` registers all route Blueprints (`app.py:203` to `app.py:232`).
3. Browser/API requests hit a route module such as `routes/main_routes.py:35` for `/api/customers`.
4. The route checks auth with `@login_required`, gets a database connection from `db_manager`, and delegates to a service (`routes/main_routes.py:36`, `routes/main_routes.py:38`, `routes/main_routes.py:40`).
5. The service executes domain SQL or logic using the provided connection, then the route returns JSON (`core/services/customer_service.py`, `routes/main_routes.py:40`).
6. Database access is created by `Database.get_connection()` and closed by the caller (`core/db/connection.py:138`, `routes/main_routes.py:42`).

### Auth Flow

1. Sign-in requests enter the auth Blueprint (`routes/auth_routes.py:15`).
2. The route reads `auth_manager` from `current_app.extensions` and verifies credentials (`routes/auth_routes.py:18`, `core/auth.py:24`).
3. Password verification supports bcrypt and password-version fallback behavior (`core/auth.py:52`).
4. `app.py` loads the Flask-Login user through `AuthManager.get_user_by_id()` (`app.py:157`, `app.py:160`).
5. Role checks are performed in route modules and templates through `current_user.role` (`routes/admin_user_routes.py`, `ui/templates/components/sidebar.html`).

### Workflow Builder And Execution

1. The workflow builder UI in `ui/templates/workspace_builder.html` uses `static/js/workspace_builder.js` to save, load, and execute workflows.
2. Workflow execution posts to `/api/workflow/execute` (`static/js/workspace_builder.js:1454`, `routes/workflow_routes.py:88`).
3. The route delegates to `execute_user_workflow()` (`routes/workflow_routes.py:95`, `core/services/workflow_service.py:24`).
4. `core/workflow_engine.py` builds a node graph and executes it in topological order (`core/workflow_engine.py:84`, `core/workflow_engine.py:112`).
5. Node handlers call Google APIs, webhooks, email, DL OCR, or DL forecast through integration helpers (`core/workflow_engine.py:158`, `core/workflow_engine.py:273`, `core/workflow_engine.py:401`, `core/workflow_engine.py:425`).

### AI Chat Flow

1. Browser chat posts to `/api/ai/chat` (`routes/ai_routes.py:151`).
2. The route validates the message through `core/services/ai_chat_service.py` and stores the user message through `db_manager.add_ai_message()` (`routes/ai_routes.py:156`, `routes/ai_routes.py:161`).
3. Short greetings return synchronously from `resolve_greeting_reply()` (`core/services/ai_chat_service.py:21`, `routes/ai_routes.py:163`).
4. Non-trivial messages create a JSON job under `jobs/` and start a background thread (`routes/ai_routes.py:21`, `routes/ai_routes.py:168`, `routes/ai_routes.py:169`).
5. `background_ai_task()` posts to the AI agent service at `HF_BASE_URL/chat` and processes returned actions through `AgentMiddleware` (`routes/ai_routes.py:45`, `routes/ai_routes.py:58`, `routes/ai_routes.py:83`).
6. The AI agent service routes `/chat` through manager/coder/RAG agents (`ai_agent_service/src/server.py:62`, `ai_agent_service/src/server.py:67`, `ai_agent_service/src/server.py:84`).

### Deep Learning Detection And Forecast Flow

1. Main app DL routes proxy browser requests under `/api/dl/*` (`routes/dl_routes.py:22`, `routes/dl_routes.py:47`).
2. `DLClient` chooses local imports by default and can fall back to HTTP when `use_local=False` (`core/services/dl_client.py:17`, `core/services/dl_client.py:26`, `core/services/dl_client.py:57`).
3. DL service API `/api/model1/detect` validates uploads and calls `process_invoice_image()` (`dl_service/api/model1_routes.py:30`, `dl_service/api/model1_routes.py:57`).
4. Invoice processing detects layout, runs OCR, parses products, enriches from catalog, records metrics, and saves invoice history (`dl_service/services/invoice_service.py:54`, `dl_service/services/invoice_service.py:75`, `dl_service/services/invoice_service.py:100`, `dl_service/services/invoice_service.py:184`).
5. OCR uses a fallback chain across EasyOCR, PaddleOCR, VietOCR, Brain VLM, and Tesseract (`dl_service/services/ocr_service.py:300`, `dl_service/services/ocr_service.py:312`).
6. Forecast requests call the LSTM model via `get_lstm_model()` and `forecast_quantity()` (`dl_service/api/model2_routes.py:21`, `dl_service/api/model2_routes.py:56`, `dl_service/api/model2_routes.py:65`).

**State Management:**
- Flask user/session state is handled by Flask-Login, `current_user`, and Flask session settings in `app.py`.
- Main business state is stored in SQLite or PostgreSQL through `core/db/connection.py`.
- PostgreSQL schema is managed through Alembic under `migrations/`; local SQLite schema is bootstrapped in `Database.init_database()` at `core/db/connection.py:178`.
- AI chat job status is stored as JSON files under `jobs/` by `routes/ai_routes.py`.
- DL invoice history is stored in both SQLite under `dl_service/database/invoices.db` and in-memory `invoice_history` in `dl_service/services/invoice_service.py:15`.
- DL model state is cached in module globals in `dl_service/services/model_loader.py` and OCR engine globals in `dl_service/services/ocr_service.py`.
- AI agent service model, memory, manager, coder, vision, and RAG objects are module-level singletons in `ai_agent_service/src/server.py`.

## Key Abstractions

**Flask App Factory:**
- Purpose: Build the application and bind runtime dependencies.
- Examples: `app.py:60`, `app.py:240`
- Pattern: Composition root plus module-level `app = create_app()` export.

**Blueprint Modules:**
- Purpose: Group HTTP routes by domain.
- Examples: `routes/main_routes.py`, `routes/admin_user_routes.py`, `routes/inventory_routes.py`, `routes/workflow_routes.py`, `routes/ai_routes.py`, `routes/dl_routes.py`
- Pattern: `Blueprint(...)` at module scope; `app.py` imports and registers each blueprint.

**Service Functions:**
- Purpose: Keep business logic out of HTTP handlers.
- Examples: `core/services/inventory_tx_service.py`, `core/services/workflow_service.py`, `core/services/ai_chat_service.py`, `core/services/product_service.py`
- Pattern: Route parses request and current user; service accepts plain values and returns plain data or raises service exceptions.

**Database Facade And Repository:**
- Purpose: Hide SQLite/PostgreSQL differences and group selected persistence operations.
- Examples: `core/db/connection.py`, `core/db/user_repo.py`, `core/db/chat_repo.py`, `core/db/workflow_repo.py`
- Pattern: `Database` opens/closes connections around repository calls; direct service code can accept `db_conn` for transaction control.

**Workflow DAG Executor:**
- Purpose: Execute user-created workflow graphs with explicit node ordering and context passing.
- Examples: `core/workflow_engine.py`, `core/services/workflow_service.py`, `static/js/workspace_builder.js`
- Pattern: Nodes and edges are persisted as JSON, then executed by topological sort with a per-node output context.

**DL Client Boundary:**
- Purpose: Decouple main app routes and workflows from DL service implementation details.
- Examples: `core/services/dl_client.py`, `routes/dl_routes.py`, `core/workflow_engine.py`
- Pattern: Main app calls `DLClient.detect_invoice()`, `DLClient.forecast_quantity()`, or `DLClient.run_ocr()`; DL internals remain in `dl_service/`.

**AI Agent Boundary:**
- Purpose: Decouple user-facing chat routes from the heavy FastAPI agent process.
- Examples: `routes/ai_routes.py`, `core/agent_middleware.py`, `ai_agent_service/src/server.py`
- Pattern: Main app posts to `HF_BASE_URL` and interprets returned text/actions; agent service owns model routing and RAG.

**Jinja Base Layout:**
- Purpose: Share global CSS, JS, CSRF metadata, theme bootstrap, and chat widget across pages.
- Examples: `ui/templates/base.html`, `ui/templates/components/sidebar.html`, `ui/templates/components/chat_widget.html`
- Pattern: Pages extend `base.html`, include page CSS/JS in blocks, and include `components/sidebar.html` for app navigation.

## Entry Points

**Main Flask App:**
- Location: `app.py`
- Triggers: `python app.py`, WSGI imports, pytest imports.
- Responsibilities: Build the app, register routes, initialize local SQLite when not using PostgreSQL, and serve on port 5000 when run directly.

**DL Service App:**
- Location: `dl_service/model_app.py`
- Triggers: `python dl_service/model_app.py`, imports from `core/services/dl_client.py` when local mode is used.
- Responsibilities: Register DL API blueprints, initialize the DL SQLite database, load model state, and serve OCR/forecast endpoints.

**DL Service Runner:**
- Location: `run_dl_service.py`
- Triggers: Direct script execution.
- Responsibilities: Add `dl_service/` to `sys.path` and run the DL service from the repo root.

**AI Agent Server:**
- Location: `ai_agent_service/src/server.py`
- Triggers: Uvicorn/FastAPI launch, including helper code under `ai_agent_service/launch_demo.py`.
- Responsibilities: Start agent singletons, host `/chat`, `/upload`, and `/ocr`.

**Database Migrations:**
- Location: `migrations/env.py`, `alembic.ini`
- Triggers: `python -m alembic upgrade head` or Alembic CLI commands.
- Responsibilities: Run raw SQL migrations against PostgreSQL using `Config.POSTGRES_URL`.

**Tests:**
- Location: `pytest.ini`, `tests/`
- Triggers: `pytest`
- Responsibilities: Build test app/client fixtures, use temp SQLite databases, and cover route/service contracts.

## Architectural Constraints

- **Threading:** Main Flask routes are synchronous. AI chat starts a background thread per non-greeting chat request in `routes/ai_routes.py:169`. `AutomationEngine` has a daemon scheduler thread in `core/automation_engine.py:21`. PostgreSQL uses `ThreadedConnectionPool(minconn=2, maxconn=10)` in `core/db/connection.py:132`.
- **Global state:** Keep new mutable runtime state out of `app.py`. Existing global state includes `config` and `app` in `app.py`, extension singletons in `core/extensions.py`, `_import_temp_files` in `routes/main_routes.py`, `JOBS_DIR` in `routes/ai_routes.py`, DL model/OCR caches in `dl_service/services/model_loader.py` and `dl_service/services/ocr_service.py`, and agent singletons in `ai_agent_service/src/server.py`.
- **Circular imports:** `core/extensions.py` exists to avoid constructing the app during route imports. Some routes still use lazy `import app as app_module` helpers, such as `routes/inventory_routes.py:17`, `routes/workflow_routes.py:14`, and `routes/dl_routes.py:15`; new code should prefer `core.extensions` imports or `current_app.extensions`.
- **Database SQL style:** Use SQLite-style `?` placeholders in main app SQL so `PGShimCursor` can translate to psycopg2 `%s` placeholders in `core/db/connection.py:24`.
- **Template root:** `app.py:64` sets `ui/templates` as the active template folder. Place new app templates under `ui/templates/`; treat root `templates/` as non-primary app templates.
- **Secrets:** `.env`, `secrets/`, and secret-bearing archive/files exist in the repo tree; do not read or copy their contents. Runtime code references secret paths through environment variables and `secrets/` paths such as `core/config.py:60` and `core/google_integration.py:33`.
- **GSD planning/tooling:** `.planning/`, `.codex/skills/`, `.github/skills/`, `.agent/`, and `.claude/` are workflow/tooling context. Application runtime code belongs in `app.py`, `core/`, `routes/`, `ui/`, `static/`, `dl_service/`, `ai_agent_service/`, `migrations/`, and `tests/`.

## Anti-Patterns

### Adding New Route Handlers To `app.py`

**What happens:** Route code can bypass the existing Blueprint split and grow the composition root again.
**Why it's wrong:** `app.py` owns app construction and blueprint registration at `app.py:203`; putting handler logic there makes route ownership harder to test and navigate.
**Do this instead:** Add handlers to a domain module in `routes/`, expose a `Blueprint`, then import/register it in `app.py` alongside the existing entries.

### Importing Mutable Runtime State From `app.py`

**What happens:** Route modules use `_app_module()` lazy imports to access globals, as seen in `routes/workflow_routes.py:14` and `routes/inventory_routes.py:17`.
**Why it's wrong:** This keeps circular-import pressure and can fail when a route expects aliases that are not present on `app.py`.
**Do this instead:** Import `db_manager` from `core.extensions`, or read app-scoped dependencies from `current_app.extensions` as `routes/auth_routes.py` does for `auth_manager`.

### Putting Flask Objects Inside Services

**What happens:** Services become tied to `request`, `current_user`, `jsonify`, or app context.
**Why it's wrong:** Service tests under `tests/services/` use plain SQLite fixtures and plain payloads; Flask coupling makes service-level regression tests brittle.
**Do this instead:** Pass explicit values such as `db_conn`, `user_id`, and `payload` into service functions as in `core/services/inventory_tx_service.py:26` and `core/services/workflow_service.py:66`.

### Mixing DL Or Agent Internals Into Main Routes

**What happens:** Main app routes directly import model internals or agent classes.
**Why it's wrong:** `dl_service/` and `ai_agent_service/` have their own startup state, dependencies, model loading, and persistence.
**Do this instead:** Use `core/services/dl_client.py` for DL calls and `routes/ai_routes.py` plus `HF_BASE_URL` for agent service calls.

### Adding Runtime Data To Source Directories

**What happens:** Generated job JSON, logs, uploads, SQLite databases, model weights, vector indexes, or secrets are placed next to source files.
**Why it's wrong:** `.gitignore` excludes runtime paths such as `jobs/`, `uploads/`, `logs/*.log`, `database/`, `*.db`, `saved_models/`, and `secrets/`.
**Do this instead:** Keep runtime data in the existing generated directories and keep source changes in `core/`, `routes/`, `ui/`, `static/`, `dl_service/`, `ai_agent_service/src/`, `migrations/`, or `tests/`.

## Error Handling

**Strategy:** Routes shape HTTP errors, services raise or return domain errors, and app-level handlers provide a JSON fallback for API exceptions.

**Patterns:**
- App-level CSRF and API exception handlers return JSON for `/api/*` paths (`app.py:188`, `app.py:197`).
- Newer services raise `ServiceValidationError` or `ServiceInvariantError` and routes map those to 400/500 responses (`core/services/service_errors.py`, `routes/inventory_routes.py:68`).
- Product/customer services return success/error tuples or raise on unexpected failures, and routes map those to JSON (`core/services/product_service.py`, `routes/main_routes.py`).
- DL routes use `ValidationError` for upload/input problems and `logger.error(..., exc_info=True)` for 500 responses (`dl_service/api/model1_routes.py:81`, `dl_service/api/ocr_routes.py:53`).
- Workflow execution returns structured status dictionaries such as `completed`, `failed`, `error`, or `skipped` (`core/workflow_engine.py:126`, `core/workflow_engine.py:477`, `core/workflow_engine.py:479`).

## Cross-Cutting Concerns

**Logging:** Main app logging is centralized through `core/logger.py`; routes and services call `get_logger(__name__)`. DL service logging is centralized through `dl_service/utils/logger.py`. AI agent service currently uses `print()` and service-local logs in `ai_agent_service/src/`.

**Validation:** Route modules validate required request fields, files, and roles. Service-layer validation lives in modules such as `core/services/inventory_tx_service.py`, `core/services/workflow_service.py`, `core/services/ai_chat_service.py`, and `dl_service/utils/validators.py`.

**Authentication:** Flask-Login is configured in `app.py` and route modules guard endpoints with `@login_required`. Role gates are implemented in route modules such as `routes/admin_user_routes.py`, `routes/admin_subscription_routes.py`, `routes/operations_routes.py`, and `routes/wallet_routes.py`.

**Authorization:** Role-based checks dominate. `core/auth.py:214` includes a permission decorator and `core/db/connection.py:420` currently returns `False` for database-backed permissions, so route-level role checks are the practical authorization boundary.

**CSRF and Security Headers:** CSRF is enabled globally in `app.py:72`, exempted on selected upload/workflow/admin POST endpoints, and injected into templates by `app.py:184`. Flask-Talisman configures CSP and frame/content-type headers in `app.py:86`.

**Configuration:** Main app config is in `core/config.py`; DL config is in `dl_service/config.py`; AI agent service config is in `ai_agent_service/src/core/config.py`. Do not read `.env` contents; use env var names from config code.

---

*Architecture analysis: 2026-06-08*
