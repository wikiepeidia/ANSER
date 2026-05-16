# Codebase Structure

**Analysis Date:** 2026-05-16

## Directory Layout

```
ANSER_Merged/                        # Project root
├── app.py                           # Main Flask entry point — application factory
├── run_dl_service.py                # Standalone launcher for DL service on port 5001
├── pytest.ini                       # Pytest configuration
├── requirements-dev.txt             # Dev/test dependencies
├── package.json                     # Minimal Node.js manifest (largely unused)
├── .env                             # Local environment variables (NOT committed)
├── .env.example                     # Documented env var template (committed)
│
├── core/                            # Application core — business logic, DB, config
│   ├── extensions.py                # Flask extension singletons (LoginManager, CSRF, Limiter, Database)
│   ├── config.py                    # Config class — env vars, paths, feature flags
│   ├── database.py                  # Database class + PGShimCursor (SQLite/PostgreSQL)
│   ├── models.py                    # User domain model (Flask-Login UserMixin)
│   ├── auth.py                      # AuthManager — login, register, password hash
│   ├── workflow_engine.py           # DAG-based workflow executor (topological sort)
│   ├── automation_engine.py         # Background scheduler thread for automations
│   ├── agent_middleware.py          # AI response parser / workflow action dispatcher
│   ├── google_integration.py        # Google Drive, Sheets, Docs, Gmail, Analytics wrappers
│   ├── make_integration.py          # Make.com / webhook trigger integration
│   ├── helpers.py                   # Miscellaneous helper functions
│   ├── utils.py                     # Shared utility functions
│   └── services/                    # Domain service modules
│       ├── service_errors.py        # Custom exception types
│       ├── ai_chat_service.py       # AI chat history storage/retrieval
│       ├── analytics_service.py     # Analytics data service
│       ├── customer_service.py      # Customer CRUD
│       ├── dl_client.py             # DLClient — proxy to DL service (local or HTTP)
│       ├── inventory_tx_service.py  # Inventory transaction logic
│       ├── operations_service.py    # Operations/automation service
│       ├── product_service.py       # Product CRUD + Excel import
│       ├── sales_service.py         # Sales order logic
│       ├── subscription_service.py  # Subscription plan management
│       ├── user_service.py          # User management service
│       ├── wallet_service.py        # Wallet/credit balance service
│       ├── workflow_service.py      # Workflow persistence (save/list/delete)
│       └── workspace_service.py     # Workspace CRUD
│
├── routes/                          # Flask Blueprints — HTTP routing layer
│   ├── __init__.py
│   ├── auth_routes.py               # auth_bp — /auth/signin, /auth/signup, OAuth callback
│   ├── page_routes.py               # page_bp — HTML page renders (dashboard, workspace, admin)
│   ├── main_routes.py               # main_bp — /api/customers, /api/products, /logout
│   ├── ai_routes.py                 # ai_bp — /api/ai/chat, /api/ai/job/{id} (async jobs)
│   ├── dl_routes.py                 # dl_bp — /api/dl/detect, /api/dl/forecast, /api/dl/ocr
│   ├── workflow_routes.py           # workflow_bp — /api/workflows CRUD + execute
│   ├── sales_routes.py              # sales_bp — /api/sales, /api/orders
│   ├── wallet_routes.py             # wallet_bp — /api/wallet/balance, /api/wallet/topup
│   ├── google_routes.py             # google_bp — /api/google/sheets, /api/google/analytics
│   ├── inventory_routes.py          # inventory_bp — /api/inventory, /api/inventory/tx
│   ├── operations_routes.py         # operations_bp — /api/operations, /api/se_automations
│   ├── workspace_routes.py          # workspace_bp — /api/workspaces, /api/items
│   ├── admin_user_routes.py         # admin_user_bp — /api/admin/users
│   └── admin_subscription_routes.py # admin_sub_bp — /api/admin/subscriptions
│
├── ui/                              # Frontend assets
│   └── templates/                   # Jinja2 HTML templates (Flask template_folder)
│       ├── base.html                # Base layout — navbar, sidebar, CSS/JS links
│       ├── index.html               # Landing page
│       ├── signin.html / signup.html
│       ├── dashboard.html
│       ├── workspace.html / workspace_builder.html
│       ├── products.html / customers.html / sale.html
│       ├── wallet.html / settings.html / exports.html / imports.html
│       ├── scenarios.html / se_auto_import.html / se_reports.html
│       ├── admin_dashboard.html / admin_managers.html / admin_roles.html
│       ├── admin_subscriptions.html / admin_workspace.html / admin_analytics.html
│       ├── manager_permissions.html / create_user_account.html
│       ├── settings_section.html / chat_widget.html / sidebar.html
│       └── components/              # Reusable Jinja2 template partials
│
├── static/                          # Static assets served by Flask
│   ├── css/                         # Per-page CSS files (admin_*.css, auth_*.css, etc.)
│   ├── js/                          # Per-page JS files (admin_*.js, auth_*.js, etc.)
│   └── img/                         # Images (favicon.svg)
│
├── dl_service/                      # Self-contained Deep Learning microservice
│   ├── model_app.py                 # DL service Flask entry point (port 5001)
│   ├── config.py                    # DL-specific config (paths, model params, Flask settings)
│   ├── api/                         # DL service blueprints
│   │   ├── model1_routes.py         # model1_bp — POST /api/model1/detect (YOLO + OCR)
│   │   ├── model2_routes.py         # model2_bp — POST /api/model2/forecast (LSTM)
│   │   ├── ocr_routes.py            # ocr_bp — POST /api/ocr/
│   │   └── history_routes.py        # history_bp — GET/POST /api/history
│   ├── services/                    # DL domain services
│   │   ├── model_loader.py          # Initializes YOLO and LSTM on startup
│   │   ├── invoice_service.py       # End-to-end invoice image processing pipeline
│   │   ├── layout_service.py        # YOLO layout detection
│   │   ├── forecast_service.py      # LSTM quantity forecasting
│   │   ├── ocr_service.py           # OCR text extraction
│   │   └── cpt_ocr.py               # Vietnamese OCR (VietOCR) wrapper
│   ├── models/                      # Model architecture definitions + weights
│   │   ├── vietocr/                 # VietOCR model source + checkpoints
│   │   ├── cpt_vision_extraction/   # Invoice extraction model
│   │   ├── cpt_vision_localization/ # Layout localization model
│   │   └── cpt_vision_recognition/  # Text recognition model
│   ├── saved_models/                # Trained weight files (.h5, .pt, .pkl)
│   ├── data/                        # Training datasets and product catalogs
│   ├── uploads/                     # Temporary file uploads for DL endpoints
│   └── utils/                       # DL service utilities
│       ├── logger.py                # get_logger() utility
│       ├── validators.py            # File type/size validators
│       ├── database.py              # DL service SQLite helper (invoice history)
│       ├── data_processor.py        # Data preprocessing helpers
│       ├── error_handlers.py        # Error formatting
│       ├── export_utils.py          # Export utilities
│       ├── invoice_processor.py     # Low-level invoice parsing
│       └── ood_detection.py         # Out-of-distribution detection
│
├── secrets/                         # Credential files (NOT committed, listed in .gitignore)
│   ├── analytics_service_account.json  # Google service account for Analytics API
│   └── token adminmail.json            # Gmail OAuth token for welcome emails
│
├── tests/                           # Automated test suite
│   ├── conftest.py                  # Pytest fixtures (app factory, test client, db)
│   ├── contracts/                   # Contract/smoke tests for route existence
│   │   ├── test_contract_routes.py
│   │   └── test_contract_smoke.py
│   ├── integration/                 # Integration tests
│   │   └── test_catalog_crud_smoke.py
│   └── services/                    # Service unit tests
│       ├── conftest.py
│       ├── test_ai_chat_service.py
│       ├── test_extraction_contracts.py
│       ├── test_inventory_route_delegation.py
│       ├── test_inventory_tx_service.py
│       ├── test_product_import.py
│       └── test_workflow_service.py
│
├── scripts/                         # One-off maintenance and migration scripts
│   ├── migrate_to_postgres.py       # SQLite → PostgreSQL data migration
│   ├── migrate_sales_invoice.py     # Sales/invoice schema migration
│   ├── fix_google_column.py         # Column backfill script
│   ├── phase11_guardrail_check.py   # Phase-gate verification
│   ├── phase11_route_snapshot.py    # Route snapshot for diff testing
│   └── phase14_backend_coverage_gate.py
│
├── package/                         # Alternate/extended requirements
│   └── requirements.txt             # Extended requirements (FastAPI, async stack)
│
├── jobs/                            # Runtime: async AI job state files ({job_id}.json)
├── images/                          # UML diagrams and project images
│   └── UML/
├── debug/                           # Debug scripts and scratch files
├── templates/                       # Legacy Flask template folder (2 stale files)
│   ├── dashboard.html               # Superseded by ui/templates/dashboard.html
│   └── index.html                   # Superseded by ui/templates/index.html
└── group_project_ai_ml.db           # SQLite database file (development/local)
```

## Key File Locations

**Entry Points:**
- `app.py`: Main Flask application — `create_app()` factory, blueprint registration, module-level `app = create_app()`
- `run_dl_service.py`: Standalone DL service launcher — adds `dl_service/` to `sys.path`, runs on port 5001
- `dl_service/model_app.py`: DL service Flask app — loads YOLO + LSTM models at startup, registers 4 blueprints

**Configuration:**
- `core/config.py`: `Config` class — all environment variable bindings, feature flags (`USE_POSTGRES`), paths
- `dl_service/config.py`: DL service config — model paths (`LSTM_MODEL_PATH`, `LAYOUT_WEIGHTS_PATH`), training params, Flask settings
- `.env`: Local environment overrides (never commit)
- `.env.example`: All required env vars documented with placeholder values

**Core Logic:**
- `core/database.py`: `Database` class — `get_connection()`, `init_database()`, `PGShimCursor`
- `core/auth.py`: `AuthManager` — user authentication and registration
- `core/workflow_engine.py`: `execute_workflow()` — DAG runner with template resolver
- `core/services/dl_client.py`: `DLClient` — abstraction over local vs. remote DL calls
- `core/extensions.py`: Shared Flask extension singletons, prevents circular imports

**Templates:**
- `ui/templates/base.html`: Base layout inherited by all pages
- `ui/templates/components/`: Reusable Jinja2 partials (chat widget, sidebar)
- `ui/templates/*.html`: One template per application page

**Testing:**
- `tests/conftest.py`: Root pytest fixtures — app factory, test client, in-memory DB
- `tests/services/`: Unit tests for service modules
- `tests/contracts/`: Smoke tests verifying route registration

## Naming Conventions

**Files:**
- Blueprint route files: `{feature}_routes.py` (e.g., `auth_routes.py`, `dl_routes.py`)
- Service files: `{feature}_service.py` (e.g., `product_service.py`, `wallet_service.py`)
- Template files: `{page_name}.html` matching the Flask `render_template()` call
- CSS/JS: `{page_name}.css` / `{page_name}.js` — one file per page

**Blueprint objects:**
- Named `{feature}_bp` — e.g., `auth_bp`, `dl_bp`, `workflow_bp`
- URL prefix set at registration in `app.py:create_app()` (only `auth_bp` uses `/auth` prefix; others are unprefixed)

**Directories:**
- Lowercase with underscores: `dl_service/`, `core/services/`, `saved_models/`

## Where to Add New Code

**New feature endpoint:**
1. Create `routes/{feature}_routes.py` with a `Blueprint('{feature}', __name__)`
2. Add business logic to `core/services/{feature}_service.py`
3. Register blueprint in `app.py:create_app()` with `flask_app.register_blueprint({feature}_bp)`
4. Add HTML template to `ui/templates/{feature}.html` if page render needed
5. Add corresponding CSS to `static/css/{feature}.css` and JS to `static/js/{feature}.js`

**New service module:**
- Location: `core/services/{feature}_service.py`
- Accept `db_manager` or a DB connection as parameter; do not import `db_manager` directly

**New database table:**
- Add `CREATE TABLE IF NOT EXISTS` block to `core/database.py:Database.init_database()` (SQLite path)
- Add a corresponding migration script in `scripts/` for PostgreSQL

**New DL model endpoint:**
- Add blueprint to `dl_service/api/{name}_routes.py`
- Add service logic to `dl_service/services/{name}_service.py`
- Register blueprint in `dl_service/model_app.py`
- Expose via `DLClient` method in `core/services/dl_client.py`

**Tests:**
- Unit tests for services: `tests/services/test_{feature}_service.py`
- Contract/route smoke tests: `tests/contracts/test_{feature}_smoke.py`

**Utility functions:**
- Shared across main app: `core/helpers.py` or `core/utils.py`
- DL service only: `dl_service/utils/`

## Special Directories

**`secrets/`:**
- Purpose: Two JSON credential files required at runtime for Google APIs (service account + Gmail OAuth token)
- Generated: Manually (service account downloaded from GCP Console; token generated via `secrets/generate token for welcome mail.py`)
- Committed: No — must be provided per-environment
- Required files: `analytics_service_account.json`, `token adminmail.json`
- All other secrets moved to `.env` (see `.env.example`)

**`jobs/`:**
- Purpose: File-based async job state for AI chat background threads
- Generated: At runtime by `routes/ai_routes.py` — one `{job_id}.json` per request
- Committed: No — ephemeral runtime data

**`dl_service/saved_models/`:**
- Purpose: Pre-trained model weight files (`.h5` for LSTM, `.pt` for YOLO, `.pkl` for scalers)
- Generated: By training scripts (`dl_service/train_lstm_model.py`, `dl_service/train_cnn_models.py`)
- Committed: No (large binary files)

**`dl_service/uploads/`:**
- Purpose: Temporary storage for files uploaded to DL API endpoints
- Generated: At runtime
- Committed: No

**`templates/` (root-level):**
- Purpose: Legacy — contains `dashboard.html` and `index.html` superseded by `ui/templates/`
- Status: Stale; Flask `template_folder` is set to `ui/templates` in `app.py`. These two files are not actively served.

**`.planning/codebase/`:**
- Purpose: GSD codebase map documents consumed by gsd-plan-phase and gsd-execute-phase
- Generated: By gsd-map-codebase
- Committed: Yes

---

*Structure analysis: 2026-05-16*
