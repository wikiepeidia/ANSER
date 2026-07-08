# Codebase Structure

**Analysis Date:** 2026-07-08

## Directory Layout

```
Group-project-AI-ML/
├── app.py                    # Main Flask app factory + entry point
├── routes/                   # Flask blueprints (HTTP layer) for the main app
├── core/                     # Shared business logic, config, integrations
│   ├── services/              # Business logic per domain
│   ├── db/                    # Repository/data-access layer (SQL)
│   └── *.py                   # config, security, auth, logger, engines, integrations
├── dl_service/                # Standalone Flask app: OCR/LSTM/forecast models
│   ├── api/                   # DL service route blueprints
│   ├── services/               # DL business logic (model loading, OCR, forecast)
│   ├── models/                 # Model code + saved weight directories
│   ├── saved_models/           # Trained model artifacts
│   ├── database/               # DL service's own SQLite db (invoices.db)
│   ├── utils/                  # DL-specific logging/db helpers
│   └── test/                   # DL service test scripts
├── ai_agent_service/          # Standalone multi-agent AI service
│   ├── src/agents/             # manager, coder, researcher, vision agents
│   ├── src/core/               # engine, memory, tools, prompts, integrations
│   └── my_workflows/           # saved agent workflow definitions
├── database/                  # Main SQLite DB file + mock data
├── migrations/                # DB migrations (versions/)
├── templates/, ui/templates/  # Jinja2 HTML templates (ui/templates/ is Flask's template_folder)
├── static/                    # CSS, JS, images served by Flask
├── tests/                     # Test suite (integration, security, contracts, parity, jobs, services)
├── jobs/                      # Ad hoc JSON files tracking async job state (one per UUID)
├── scripts/                   # Maintenance/dev scripts
├── secrets/                   # Local secret material (never commit contents)
├── uploads/                   # User-uploaded files (runtime data)
├── logs/                      # Application log output
├── workflow_templates/        # Predefined workflow JSON/config templates
├── examples/                  # Demo/example code
├── evaluate/                  # Model evaluation scripts + results
├── DOCUMENTS/                 # Project documentation (backend, backup, bugs, model, reports)
├── images/                    # UML diagrams, favicons, static assets for docs
├── strix_runs/                # Security scan run outputs (Strix)
├── .planning/                 # GSD planning artifacts (roadmap, phases, codebase docs)
└── .claude/, .agent*, .codex/, .cursor/, .gemini/, .github/  # GSD tool installs (multi-CLI)
```

## Directory Purposes

**`routes/`:**
- Purpose: HTTP endpoint definitions for the main Flask app, one file per domain
- Contains: Flask `Blueprint` objects (auth, main, page, sales, workspace, wallet, google, admin_user, admin_subscription, admin_warehouse, operations, ai, inventory, workflow, dl, n8n_api)
- Key files: `routes/n8n_api.py` (531 lines, largest — n8n webhook integration), `routes/main_routes.py` (321 lines), `routes/inventory_routes.py` (287 lines)

**`core/`:**
- Purpose: Shared application logic not tied to a specific HTTP route
- Contains: config (`core/config.py`), security helpers (`core/security.py`), auth manager (`core/auth.py`), Flask extensions singleton registry (`core/extensions.py`), Flask-Login `User` model (`core/models.py`), automation/workflow engines (`core/automation_engine.py`, `core/workflow_engine.py`, 541 lines — largest core file), Google integration (`core/google_integration.py`, 515 lines), Make.com integration (`core/make_integration.py`), Excel import parsing (`core/excel_parser.py`), agent middleware bridging to `ai_agent_service` (`core/agent_middleware.py`)
- Key files: `core/database.py` is a thin backward-compat shim re-exporting from `core/db/connection.py`

**`core/services/`:**
- Purpose: Business logic layer, one module per domain, called from `routes/`
- Contains: `ai_chat_service.py`, `analytics_service.py`, `customer_service.py`, `dl_client.py` (HTTP client for DL service), `inventory_tx_service.py`, `operations_service.py`, `product_service.py`, `sales_service.py`, `service_errors.py`, `subscription_service.py`, `user_service.py`, `wallet_service.py`, `workflow_service.py`, `workspace_service.py`

**`core/db/`:**
- Purpose: Repository pattern for SQL access
- Contains: `connection.py` (Database/PGShim classes supporting both SQLite and Postgres), `user_repo.py`, `activity_repo.py`, `chat_repo.py`, `workflow_repo.py`

**`dl_service/`:**
- Purpose: Standalone Flask microservice for deep-learning inference (OCR, LSTM forecasting, invoice extraction)
- Contains: `api/` (route blueprints: `model1_routes.py`, `model2_routes.py`, `history_routes.py`, `ocr_routes.py`), `services/` (`cpt_ocr.py`, `forecast_service.py`, `invoice_service.py`, `layout_service.py`, `model_loader.py`, `ocr_service.py`), `models/` (`OCR.py`, `lstm_model.py`, plus `cpt_vision_*` and `vietocr` subdirs), `saved_models/` (trained weight artifacts), `database/invoices.db` (own SQLite DB), `train_cnn_models.py`, `train_lstm_model.py` (training scripts at package root), `test/` (test scripts)
- Key files: `dl_service/model_app.py` is the Flask entry point (imports `config.py` and `services/model_loader.py` for model init)

**`ai_agent_service/`:**
- Purpose: Standalone multi-agent orchestration service, separate from the Flask request/response cycle
- Contains: `src/agents/` (`base.py`, `coder.py`, `manager.py`, `researcher.py`, `vision.py`), `src/core/` (`engine.py`, `memory.py`, `tools.py`, `prompts.py`, `context.py`, `knowledge.py`, `integrations.py`, `saas_api.py`, `config.py`, `agent_middleware.py`), `src/server.py` (service entry), `src/data/*.jsonl` (training/reasoning datasets), `src/archive/` (older training/verification scripts), `my_workflows/` (saved workflow definitions)

**`database/`:**
- Purpose: Main application database file and mock/seed data
- Contains: `group_project_ai_ml.db` (SQLite dev DB), `mock/` (seed data), `progres.py` (Postgres-related helper)

**`migrations/`:**
- Purpose: Database schema migrations
- Contains: `versions/` (migration scripts)

**`templates/` and `ui/templates/`:**
- Purpose: Jinja2 HTML templates
- Note: `app.py` sets `template_folder='ui/templates'` — that is the active template root for the main Flask app; `templates/` at repo root may be legacy/unused or used by a different service — verify before assuming it's live

**`static/`:**
- Purpose: Static assets served by Flask
- Contains: `css/`, `js/`, `img/`

**`tests/`:**
- Purpose: Test suite for the main app
- Contains: `contracts/`, `integration/`, `jobs/`, `parity/`, `security/`, `services/` subdirectories

**`jobs/`:**
- Purpose: Ad hoc async job state persisted as individual JSON files (UUID filename per job)
- Generated: Yes (runtime-created)
- Committed: Appears to be committed to the repo currently — verify whether this should be gitignored

**`.planning/`:**
- Purpose: GSD workflow artifacts — roadmap, phase plans, requirements, codebase docs (this document lives here)
- Contains: `codebase/` (this doc + siblings), `phases/`, `quick/`, `research/`

**Multi-CLI GSD installs (`.claude/`, `.agent/`, `.agents/`, `.codex/`, `.cursor/`, `.gemini/`, `.github/skills`):**
- Purpose: Parallel installs of the GSD workflow/skills system for different AI CLI tools (Claude Code, Codex, Cursor, Gemini, GitHub Copilot)
- Not application code — safe to ignore when navigating business logic

## Key File Locations

**Entry Points:**
- `app.py`: Main Flask app factory (`create_app()`) and `if __name__ == '__main__'` runner
- `dl_service/model_app.py`: DL service Flask app (also runnable via `run_dl_service.py` at repo root)
- `ai_agent_service/main.py` (invokes `ai_agent_service/src/server.py`): AI agent service entry

**Configuration:**
- `core/config.py`: Main app config (`Config` class)
- `dl_service/config.py`: DL service config (template/static dirs, Flask host/port)
- `.env` (not read by this mapper — env var driven config, see `core/security.py:env_flag`)

**Core Logic:**
- `core/services/*.py`: Business logic
- `core/db/*.py`: Data access
- `core/automation_engine.py`, `core/workflow_engine.py`: Automation/workflow orchestration

**Testing:**
- `tests/`: pytest-based suite (`tests/integration`, `tests/security`, `tests/contracts`, `tests/parity`, `tests/services`, `tests/jobs`)
- `dl_service/test/`: DL service-specific tests
- `dl_service/test_ocr_pipeline.py`, `test_vietocr.py`, `test_vietocr2.py`: standalone DL test scripts at package root

## Naming Conventions

**Files:**
- Route blueprints: `<domain>_routes.py` (e.g. `sales_routes.py`, `admin_user_routes.py`)
- Services: `<domain>_service.py` (e.g. `wallet_service.py`, `product_service.py`)
- Repositories: `<domain>_repo.py` (e.g. `user_repo.py`, `workflow_repo.py`)
- Python files use `snake_case.py` throughout

**Directories:**
- Domain-plural or role-based lowercase names (`routes/`, `services/`, `agents/`), no nested feature-first grouping — layering is by technical role (routes vs services vs db), not by business feature

## Where to Add New Code

**New Feature (main app):**
- Route: add `routes/<feature>_routes.py`, define a `Blueprint`, register it in `app.py` inside `create_app()`'s blueprint registration block
- Business logic: add `core/services/<feature>_service.py`
- Data access: add `core/db/<feature>_repo.py` if new SQL entities are needed
- Tests: add to `tests/integration/` or `tests/services/` matching the layer touched

**New DL model endpoint:**
- Route: add to `dl_service/api/<name>_routes.py`
- Logic: add to `dl_service/services/<name>_service.py`
- Model code: `dl_service/models/`, weights in `dl_service/saved_models/`

**New AI agent capability:**
- Agent: add to `ai_agent_service/src/agents/`
- Shared engine/tool logic: `ai_agent_service/src/core/`

**Utilities:**
- Cross-cutting helpers: `core/utils.py`, `core/helpers.py`
- DL-service-specific helpers: `dl_service/utils/`

## Special Directories

**`jobs/`:**
- Purpose: Async job state as individual JSON files
- Generated: Yes
- Committed: Currently present in repo — treat as runtime data, do not hand-edit

**`uploads/`, `dl_service/uploads/`:**
- Purpose: User-uploaded files (invoices, images for OCR)
- Generated: Yes
- Committed: Should generally be gitignored (verify against `.gitignore`)

**`logs/`, `utils/logs/`:**
- Purpose: Application log output
- Generated: Yes
- Committed: Should generally be gitignored

**`secrets/`:**
- Purpose: Local secret material referenced by CLAUDE.md ("Do not commit secrets from `secrets/`")
- Generated: No (manually placed)
- Committed: Must NOT be committed

**`database/`, `dl_service/database/`:**
- Purpose: SQLite database files for main app and DL service respectively
- Generated: Yes (created on first run) but currently checked in — treat as environment-specific data

**`strix_runs/`:**
- Purpose: Output of Strix security scans
- Generated: Yes
- Committed: Appears checked in — likely safe to periodically clean up

---

*Structure analysis: 2026-07-08*
