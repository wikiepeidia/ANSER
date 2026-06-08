# Codebase Structure

**Analysis Date:** 2026-06-08

## Directory Layout

```text
Group-project-AI-ML/
|-- app.py                         # Main Flask app factory, dependency binding, blueprint registration
|-- run_dl_service.py              # Helper runner for `dl_service/model_app.py`
|-- alembic.ini                    # Alembic configuration for PostgreSQL migrations
|-- pytest.ini                     # Pytest discovery/config
|-- README.md                      # Setup, architecture notes, team conventions
|-- START_HERE.md                  # Onboarding/startup guidance
|-- package.json                   # Minimal npm metadata placeholder
|-- package-lock.json              # npm lockfile placeholder
|-- package/                       # Python packaging/install helpers and requirements
|-- core/                          # Main app shared backend code
|   |-- db/                        # Database facade, PostgreSQL shim, repositories
|   |-- services/                  # Main app business services
|   |-- config.py                  # Main app env/config class
|   |-- extensions.py              # Flask extension singletons
|   |-- auth.py                    # AuthManager and auth decorators
|   |-- workflow_engine.py         # Workflow DAG executor
|   |-- automation_engine.py       # Background automation scheduler
|   |-- agent_middleware.py        # AI response/action middleware
|   |-- google_integration.py      # Google Drive/Sheets/Docs/Gmail helpers
|   |-- make_integration.py        # Generic webhook helper
|   |-- models.py                  # Flask-Login user model
|   |-- logger.py                  # Main app logging setup
|   |-- helpers.py                 # Shared formatting/business helpers
|   |-- utils.py                   # Shared utility helpers
|   `-- excel_parser.py            # Excel upload parser
|-- routes/                        # Flask Blueprint route modules
|-- ui/templates/                  # Active Jinja template root
|   `-- components/                # Shared Jinja fragments
|-- static/                        # CSS, JS, and image assets served by Flask
|   |-- css/
|   |-- js/
|   `-- img/
|-- templates/                     # Non-primary/legacy root templates
|-- dl_service/                    # Separate Flask service for OCR, invoice extraction, and LSTM forecast
|   |-- api/                       # DL API Blueprints
|   |-- services/                  # DL service functions
|   |-- utils/                     # DL validators, database, logging, processors
|   |-- models/                    # DL model definitions and vendored model code
|   |-- data/                      # DL datasets/catalogs
|   |-- config.py                  # DL configuration
|   `-- model_app.py               # DL Flask app entry point
|-- ai_agent_service/              # Separate FastAPI AI agent service
|   |-- src/
|   |   |-- agents/                # Manager, coder, researcher, vision agents
|   |   |-- core/                  # Engine, memory, RAG, SaaS/integration helpers
|   |   |-- data/                  # Agent datasets, schemas, blueprints
|   |   |-- models/                # Agent model adapters/assets
|   |   |-- archive/               # Experimental/training utilities
|   |   `-- server.py              # FastAPI app entry point
|   |-- data/                      # Vector DB/runtime agent data
|   `-- launch_demo.py             # Uvicorn/demo launcher
|-- migrations/                    # Alembic environment and versions
|-- tests/                         # Pytest route, contract, integration, parity, and service tests
|-- debug/                         # Manual diagnostics and migration/debug scripts
|-- scripts/                       # Project scripts
|-- evaluate/                      # Evaluation scripts and result JSON
|-- DOCUMENTS/                     # Project reports/presentation materials
|-- images/                        # Documentation/UML assets
|-- examples/                      # Demo/snapshot code and assets
|-- jobs/                          # Runtime AI job JSON files
|-- logs/                          # Runtime logs
|-- uploads/                       # Runtime uploaded files
|-- database/                      # Runtime/local database artifacts
|-- secrets/                       # Secret files directory; do not read contents
|-- .planning/                     # GSD project state, plans, and generated codebase docs
|-- .codex/skills/                 # Project-local Codex/GSD skills
|-- .github/                       # GitHub metadata, GSD agents, templates, skills
|-- .agent/                        # Local GSD/agent runtime tooling
`-- .claude/                       # Local Claude/GSD runtime tooling
```

## Directory Purposes

**Root Application Files:**
- Purpose: Provide top-level application entry points and project metadata.
- Contains: `app.py`, `run_dl_service.py`, `README.md`, `START_HERE.md`, `pytest.ini`, `alembic.ini`, `package.json`.
- Key files: `app.py`, `run_dl_service.py`, `README.md`, `pytest.ini`, `alembic.ini`.

**`core/`:**
- Purpose: Main Flask app backend internals shared by routes and services.
- Contains: Configuration, auth, database access, workflow execution, automation, AI middleware, Google/Make integrations, helpers, logging.
- Key files: `core/config.py`, `core/extensions.py`, `core/auth.py`, `core/workflow_engine.py`, `core/automation_engine.py`, `core/agent_middleware.py`, `core/google_integration.py`, `core/make_integration.py`, `core/logger.py`, `core/models.py`.

**`core/db/`:**
- Purpose: Persistence facade and repository classes for main app state.
- Contains: SQLite/PostgreSQL connection compatibility code, `Database`, `PGShimConnection`, `PGShimCursor`, and repositories.
- Key files: `core/db/connection.py`, `core/db/user_repo.py`, `core/db/activity_repo.py`, `core/db/chat_repo.py`, `core/db/workflow_repo.py`.

**`core/services/`:**
- Purpose: Domain business logic below Flask routes.
- Contains: Services for customers, products, inventory transactions, sales, wallet, subscription, users, operations, workflow, AI chat, analytics, DL client, and typed service errors.
- Key files: `core/services/product_service.py`, `core/services/customer_service.py`, `core/services/inventory_tx_service.py`, `core/services/workflow_service.py`, `core/services/ai_chat_service.py`, `core/services/dl_client.py`, `core/services/service_errors.py`.

**`routes/`:**
- Purpose: Flask Blueprint modules for HTTP pages and APIs.
- Contains: Auth, pages, product/customer APIs, inventory APIs, workflow APIs, AI chat APIs, DL proxy APIs, admin user/subscription APIs, operations, wallet, Google OAuth, and sales endpoints.
- Key files: `routes/auth_routes.py`, `routes/page_routes.py`, `routes/main_routes.py`, `routes/inventory_routes.py`, `routes/workflow_routes.py`, `routes/ai_routes.py`, `routes/dl_routes.py`, `routes/google_routes.py`, `routes/admin_user_routes.py`, `routes/admin_subscription_routes.py`, `routes/operations_routes.py`, `routes/wallet_routes.py`, `routes/sales_routes.py`.

**`ui/templates/`:**
- Purpose: Active Jinja template root for the main Flask app.
- Contains: Page templates, `base.html`, and shared components.
- Key files: `ui/templates/base.html`, `ui/templates/components/sidebar.html`, `ui/templates/components/chat_widget.html`, `ui/templates/workspace_builder.html`, `ui/templates/dashboard.html`, `ui/templates/imports.html`, `ui/templates/products.html`.

**`static/`:**
- Purpose: Static frontend assets served by Flask.
- Contains: Per-page CSS files in `static/css/`, per-page JS files in `static/js/`, and image assets in `static/img/`.
- Key files: `static/css/base_theme.css`, `static/css/style.css`, `static/js/base_theme.js`, `static/js/script.js`, `static/js/workspace_builder.js`, `static/js/chat.js`, `static/img/favicon.svg`.

**`templates/`:**
- Purpose: Root-level template directory that is not the active Flask template root.
- Contains: `templates/index.html`, `templates/dashboard.html`.
- Key files: `templates/index.html`, `templates/dashboard.html`.

**`dl_service/`:**
- Purpose: Separate deep-learning Flask service for invoice OCR/extraction and import forecasting.
- Contains: Service app, API routes, OCR/forecast/model services, model definitions, validators, SQLite invoice database helpers, datasets, training scripts.
- Key files: `dl_service/model_app.py`, `dl_service/config.py`, `dl_service/api/model1_routes.py`, `dl_service/api/model2_routes.py`, `dl_service/api/ocr_routes.py`, `dl_service/api/history_routes.py`, `dl_service/services/invoice_service.py`, `dl_service/services/ocr_service.py`, `dl_service/services/model_loader.py`, `dl_service/services/forecast_service.py`, `dl_service/utils/database.py`.

**`dl_service/models/`:**
- Purpose: DL model code and vendored OCR/model implementations.
- Contains: LSTM model code, OCR model code, CTPN/localization/extraction/recognition code, and vendored VietOCR code.
- Key files: `dl_service/models/lstm_model.py`, `dl_service/models/OCR.py`, `dl_service/models/cpt_vision_localization/_model.py`, `dl_service/models/cpt_vision_recognition/_model.py`, `dl_service/models/vietocr/vietocr/tool/predictor.py`.

**`ai_agent_service/`:**
- Purpose: Separate FastAPI service for AI chat, image upload analysis, OCR, RAG, and multi-agent reasoning.
- Contains: FastAPI server, model engine, memory, RAG, agents, datasets, vector DB data, launch helper, training/archive utilities.
- Key files: `ai_agent_service/src/server.py`, `ai_agent_service/src/core/engine.py`, `ai_agent_service/src/core/memory.py`, `ai_agent_service/src/core/knowledge.py`, `ai_agent_service/src/core/config.py`, `ai_agent_service/src/agents/manager.py`, `ai_agent_service/src/agents/coder.py`, `ai_agent_service/src/agents/vision.py`, `ai_agent_service/launch_demo.py`.

**`migrations/`:**
- Purpose: Alembic migration environment for PostgreSQL schema.
- Contains: Alembic `env.py`, migration template, and version scripts.
- Key files: `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/001_initial_schema.py`, `migrations/001_add_password_version.py`.

**`tests/`:**
- Purpose: Automated regression tests for app, route, contract, integration, parity, and service behavior.
- Contains: Top-level pytest tests, service unit tests, contract tests, integration tests, parity tests, shared fixtures.
- Key files: `tests/conftest.py`, `tests/services/conftest.py`, `tests/services/test_inventory_tx_service.py`, `tests/services/test_workflow_service.py`, `tests/services/test_ai_chat_service.py`, `tests/contracts/test_contract_routes.py`, `tests/integration/test_catalog_crud_smoke.py`, `tests/parity/test_endpoint_middleware_parity.py`.

**`debug/`:**
- Purpose: Manual diagnostic, migration, route snapshot, and coverage helper scripts.
- Contains: Debug scripts for login, schema checks, route guardrails, password-version fixes, coverage gates.
- Key files: `debug/phase11_route_snapshot.py`, `debug/phase11_guardrail_check.py`, `debug/phase14_backend_coverage_gate.py`, `debug/check_neon_schema.py`, `debug/test_login.py`.

**`package/`:**
- Purpose: Install/package helpers and main Python dependency list.
- Contains: `package/requirements.txt`, installer script, PostgreSQL migration helper.
- Key files: `package/requirements.txt`, `package/installer.py`, `package/migrate_to_postgres.py`.

**`evaluate/`:**
- Purpose: Evaluation scripts and stored evaluation results.
- Contains: Routing/evaluation scripts and JSON result artifacts.
- Key files: `evaluate/run_eval.py`, `evaluate/full_eval.py`, `evaluate/eval_real_images.py`, `evaluate/results/`.

**`DOCUMENTS/` and `images/`:**
- Purpose: Project reports, presentation materials, and diagram/image assets.
- Contains: Documentation artifacts and UML SVGs.
- Key files: `images/UML/Backend.svg`, `images/UML/Frontend.svg`.

**`examples/`:**
- Purpose: Demo/snapshot reference material.
- Contains: Example app snapshot under `examples/demo/Group-project-AI-ML-main/`.
- Key files: `examples/demo/Group-project-AI-ML-main/app.py`, `examples/demo/Group-project-AI-ML-main/ui/templates/workspace_builder.html`.

**Runtime Data Directories:**
- Purpose: Hold local runtime output outside source ownership.
- Contains: `jobs/`, `logs/`, `uploads/`, `database/`, `.pytest_cache/`, `__pycache__/`, `.coverage`.
- Key files: Not applicable for source changes.

**Planning And Agent Tooling:**
- Purpose: GSD planning state, local workflow skills, and agent metadata.
- Contains: `.planning/`, `.codex/skills/`, `.github/skills/`, `.github/agents/`, `.agent/`, `.claude/`.
- Key files: `.planning/STATE.md`, `.planning/PROJECT.md`, `.codex/skills/gsd-map-codebase/SKILL.md`, `.github/agents/gsd-codebase-mapper.agent.md`.

## Key File Locations

**Entry Points:**
- `app.py`: Main Flask app factory and `app = create_app()` export.
- `run_dl_service.py`: Root-level runner for the DL service.
- `dl_service/model_app.py`: DL Flask app entry point and model/database startup.
- `ai_agent_service/src/server.py`: AI agent FastAPI app entry point.
- `ai_agent_service/launch_demo.py`: Helper launcher for the agent service.
- `migrations/env.py`: Alembic migration runtime.
- `pytest.ini`: Pytest root configuration.

**Configuration:**
- `core/config.py`: Main app configuration and environment-variable names.
- `dl_service/config.py`: DL service paths, model settings, Flask host/port, and data/model directories.
- `ai_agent_service/src/core/config.py`: AI agent model, data, and database configuration.
- `alembic.ini`: Alembic configuration file.
- `pytest.ini`: Test discovery settings.
- `.env`: Local environment file present; do not read contents.
- `.env.example`: Example environment file present.
- `secrets/`: Secret directory present; do not read contents.

**Core Logic:**
- `app.py`: Composition root, security/session setup, error handlers, blueprint registration.
- `core/extensions.py`: Shared Flask extension singletons.
- `core/db/connection.py`: Database facade, SQLite schema, PostgreSQL shim.
- `core/services/*.py`: Domain service functions.
- `routes/*.py`: HTTP API and page handlers.
- `core/workflow_engine.py`: Workflow DAG execution and integration node handlers.
- `core/agent_middleware.py`: AI context and action processing.
- `core/services/dl_client.py`: Main-app boundary for DL calls.
- `dl_service/services/invoice_service.py`: Invoice detection service flow.
- `dl_service/services/ocr_service.py`: OCR fallback chain.
- `dl_service/services/model_loader.py`: DL model startup/cache.
- `ai_agent_service/src/server.py`: AI agent API surface.
- `ai_agent_service/src/core/engine.py`: Heavy model engine singleton.

**Frontend:**
- `ui/templates/base.html`: Shared layout, CSS/JS includes, CSRF token, theme bootstrap, chat widget include.
- `ui/templates/components/sidebar.html`: Shared navigation and role-aware menu.
- `ui/templates/components/chat_widget.html`: Chat widget template.
- `ui/templates/<page>.html`: Page template for a route in `routes/page_routes.py`.
- `static/css/<page>.css`: Page-specific CSS.
- `static/js/<page>.js`: Page-specific browser logic and fetch calls.

**Testing:**
- `tests/conftest.py`: Flask app/client and temp SQLite fixtures.
- `tests/services/conftest.py`: In-memory SQLite service fixtures.
- `tests/services/`: Service-level unit tests.
- `tests/contracts/`: Route and smoke contract tests.
- `tests/integration/`: Integration smoke tests.
- `tests/parity/`: Middleware and async/data parity tests.
- `debug/phase14_backend_coverage_gate.py`: Manual coverage gate helper.

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`: `core/workflow_engine.py`, `core/services/product_service.py`, `routes/admin_user_routes.py`.
- Route modules use `<domain>_routes.py`: `routes/auth_routes.py`, `routes/inventory_routes.py`, `routes/workflow_routes.py`, `routes/dl_routes.py`.
- Service modules use `<domain>_service.py` or `<domain>_tx_service.py`: `core/services/user_service.py`, `core/services/inventory_tx_service.py`.
- Repository modules use `<domain>_repo.py`: `core/db/user_repo.py`, `core/db/chat_repo.py`.
- Pytest files use `test_*.py`: `tests/test_inventory.py`, `tests/services/test_workflow_service.py`.
- Jinja pages use lowercase route/domain names: `ui/templates/workspace_builder.html`, `ui/templates/admin_dashboard.html`.
- Static page assets mirror page/domain names: `static/css/admin_dashboard.css`, `static/js/admin_dashboard.js`.
- Shared Jinja components live in `ui/templates/components/*.html`.

**Directories:**
- Main app backend code belongs under `core/` and `routes/`.
- Main app business services belong under `core/services/`.
- Main app repositories belong under `core/db/`.
- Active UI templates belong under `ui/templates/`.
- Static browser assets belong under `static/css/`, `static/js/`, and `static/img/`.
- DL service code belongs under `dl_service/api/`, `dl_service/services/`, `dl_service/utils/`, and `dl_service/models/`.
- AI agent code belongs under `ai_agent_service/src/agents/` and `ai_agent_service/src/core/`.
- Tests belong under `tests/`, with service-specific tests in `tests/services/`.
- GSD planning/codebase maps belong under `.planning/codebase/`.

## Where to Add New Code

**New Main App Feature:**
- Primary route code: `routes/<domain>_routes.py`
- Business logic: `core/services/<domain>_service.py`
- Database facade/repository code: `core/db/connection.py` and `core/db/<domain>_repo.py` when shared facade methods are needed.
- Registration: import and `register_blueprint(...)` in `app.py`.
- Tests: `tests/services/test_<domain>_service.py` for service logic and `tests/test_<domain>.py` or `tests/contracts/` for route behavior.

**New API Endpoint:**
- Implementation: add to an existing `routes/*_routes.py` domain module when the domain exists.
- New domain: create `routes/<domain>_routes.py`, expose `<domain>_bp`, and register it in `app.py`.
- Request parsing and HTTP status mapping stay in `routes/`; validation/business operations go in `core/services/`.

**New Jinja Page:**
- Template: `ui/templates/<page>.html`
- Page route: `routes/page_routes.py`
- CSS: `static/css/<page>.css`
- JavaScript: `static/js/<page>.js`
- Navigation: `ui/templates/components/sidebar.html` if the page should appear in the sidebar.
- Shared layout: extend `ui/templates/base.html`.

**New Database Table Or Column:**
- PostgreSQL migration: `migrations/versions/<revision>_<description>.py`
- Local SQLite compatibility: update schema bootstrap in `core/db/connection.py`.
- Access logic: add service functions in `core/services/`; add repository methods in `core/db/<domain>_repo.py` if the domain is repository-backed.
- Tests: add fixture schema updates in `tests/services/conftest.py` when service tests use in-memory SQLite.

**New Workflow Node Type:**
- Execution handler: `core/workflow_engine.py`
- Workflow service validation/persistence: `core/services/workflow_service.py` when payload rules change.
- Builder UI: `ui/templates/workspace_builder.html` and `static/js/workspace_builder.js`
- Tests: `tests/services/test_workflow_service.py` and route/contract tests under `tests/`.

**New DL Endpoint Or Model Feature:**
- DL route: `dl_service/api/<feature>_routes.py`
- DL service logic: `dl_service/services/<feature>_service.py`
- DL utilities: `dl_service/utils/`
- Main app proxy/client: `core/services/dl_client.py` and `routes/dl_routes.py` if the feature is exposed through the main app.
- Config/model paths: `dl_service/config.py`
- Tests: service tests under `tests/services/` or DL-specific tests under `dl_service/` if they require model fixtures.

**New AI Agent Capability:**
- Agent behavior: `ai_agent_service/src/agents/`
- Shared agent engine/memory/RAG/tooling: `ai_agent_service/src/core/`
- HTTP contract: `ai_agent_service/src/server.py`
- Main app integration: `routes/ai_routes.py` and `core/agent_middleware.py`
- Do not import agent service classes directly into normal Flask route handlers; use the HTTP boundary configured by `HF_BASE_URL`.

**Utilities:**
- Main app shared helpers: `core/helpers.py` for business formatting/helpers and `core/utils.py` for generic utilities.
- DL shared helpers: `dl_service/utils/`.
- Frontend shared behavior: `static/js/script.js`, `static/js/base_theme.js`, or a page-specific file under `static/js/`.

## Special Directories

**`.planning/`:**
- Purpose: GSD project state, roadmap, requirements, phase artifacts, and generated codebase maps.
- Generated: Yes.
- Committed: Project-dependent; modify only requested planning artifacts.

**`.planning/codebase/`:**
- Purpose: Generated codebase reference docs consumed by GSD planning/execution commands.
- Generated: Yes.
- Committed: Intended planning artifact.

**`.codex/skills/`:**
- Purpose: Project-local Codex/GSD skill definitions.
- Generated: Tooling-managed.
- Committed: Project-dependent; do not edit during application feature work unless updating skills.

**`.github/`:**
- Purpose: GitHub templates plus GSD agent/skill metadata.
- Generated: Partly tooling-managed.
- Committed: Yes for repository metadata.

**`.agent/` and `.claude/`:**
- Purpose: Local GSD/agent runtime tooling and migration journal data.
- Generated: Yes.
- Committed: No for local runtime contents.

**`secrets/`:**
- Purpose: Secret-bearing OAuth/service-account/token files.
- Generated: Manual/runtime.
- Committed: No; `.gitignore` excludes `secrets/`.

**`.env` and `.env.*`:**
- Purpose: Local environment configuration.
- Generated: Manual.
- Committed: No; do not read contents.

**`jobs/`:**
- Purpose: Runtime AI chat job status JSON written by `routes/ai_routes.py`.
- Generated: Yes.
- Committed: No; `.gitignore` excludes `jobs/`.

**`logs/`:**
- Purpose: Runtime application logs.
- Generated: Yes.
- Committed: No for `logs/*.log` and rotations.

**`uploads/`:**
- Purpose: Runtime uploaded files for workflow and app uploads.
- Generated: Yes.
- Committed: No; `.gitignore` excludes `uploads/`.

**`database/`:**
- Purpose: Runtime/local database artifacts.
- Generated: Yes.
- Committed: No; `.gitignore` excludes `database/` and `*.db`.

**`dl_service/saved_models/` and `saved_models/`:**
- Purpose: DL model weights and generated trained models.
- Generated: Yes.
- Committed: No; `.gitignore` excludes saved model directories.

**`ai_agent_service/data/vector_db/`:**
- Purpose: Chroma/vector database runtime data for the AI agent service.
- Generated: Yes.
- Committed: Runtime artifact; avoid editing by hand.

**`examples/`:**
- Purpose: Demo/reference snapshots.
- Generated: No.
- Committed: Reference material; do not add production code here.

**`debug/`:**
- Purpose: Manual operational/debugging scripts and coverage/route guardrails.
- Generated: No.
- Committed: Developer tooling; production app behavior belongs in `core/`, `routes/`, `dl_service/`, or `ai_agent_service/src/`.

---

*Structure analysis: 2026-06-08*
