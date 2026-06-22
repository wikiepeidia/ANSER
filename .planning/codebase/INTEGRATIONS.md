# External Integrations

**Analysis Date:** 2026-06-08

## APIs & External Services

**Google Identity:**
- Google OAuth/OpenID - Used for login, account connection, and profile bootstrap.
  - Implementation: `app.py` registers the Authlib Google client; `routes/google_routes.py` handles `/auth/login/google`, `/auth/connect/google`, and `/auth/google/callback`.
  - SDK/Client: `authlib`, `oauthlib`, `google-auth-oauthlib`.
  - Auth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, or OAuth client data in `secrets/google_oauth.json`.

**Google Workspace APIs:**
- Google Drive - Lists Google files for workflow builder pickers.
  - Implementation: `core/google_integration.py` `list_files()` and `routes/google_routes.py` `/api/google/files`.
  - SDK/Client: `google-api-python-client`.
  - Auth: User OAuth token stored as `users.google_token` through `routes/google_routes.py`; token files are also referenced at `secrets/token.json` and `secrets/token adminmail.json`.
- Google Sheets - Reads and writes spreadsheet ranges for workflow nodes.
  - Implementation: `core/google_integration.py` `read_sheet()` and `write_sheet()`; node execution in `core/workflow_engine.py`.
  - SDK/Client: `google-api-python-client`.
  - Auth: User OAuth token from `users.google_token` and scopes registered in `app.py`.
- Google Docs - Reads and appends document content for workflow nodes.
  - Implementation: `core/google_integration.py` `read_doc()` and `write_doc()`; node execution in `core/workflow_engine.py`.
  - SDK/Client: `google-api-python-client`.
  - Auth: User OAuth token from `users.google_token`.
- Gmail API - Sends welcome emails and workflow emails.
  - Implementation: `core/google_integration.py` `send_email()` and `core/auth.py` registration welcome email.
  - SDK/Client: `google-api-python-client`.
  - Auth: User OAuth token or admin token file `secrets/token adminmail.json`.

**Analytics:**
- Google Analytics 4 Data API - Provides admin analytics data and optional frontend tracking.
  - Implementation: `core/services/analytics_service.py`, `core/google_integration.py` `get_analytics_report()`, and `routes/operations_routes.py` `/api/admin/analytics/data`.
  - SDK/Client: `google-analytics-data` with `google.oauth2.service_account`.
  - Auth: `GA_PROPERTY_ID` plus service-account file `secrets/analytics_service_account.json`.
- Google Tag Manager / gtag.js - Browser tracking script is loaded from Google.
  - Implementation: `ui/templates/base.html`.
  - SDK/Client: Browser script `https://www.googletagmanager.com/gtag/js`.
  - Auth: Measurement ID is embedded in `ui/templates/base.html`; server-side GA4 reads `GA_PROPERTY_ID` from `core/config.py`.

**AI / LLM Services:**
- Hugging Face-compatible AI HTTP service - Main app sends chat and upload requests to a remote or tunneled AI service.
  - Implementation: `routes/ai_routes.py` calls `${HF_BASE_URL}/chat` and `${HF_BASE_URL}/upload`.
  - SDK/Client: `requests`.
  - Auth: `HF_BASE_URL`; optional bearer token `HF_TOKEN`.
- Local FastAPI AI agent service - Provides `/chat`, `/upload`, and `/ocr` endpoints used by the main app and OCR fallback.
  - Implementation: `ai_agent_service/src/server.py`; runtime model config in `ai_agent_service/src/core/engine.py`.
  - SDK/Client: `fastapi`, `uvicorn`, `vllm`, `transformers`, `torch`.
  - Auth: No endpoint authentication detected in `ai_agent_service/src/server.py`; exposure tooling is in `ai_agent_service/launch_demo.py`.
- Qwen model downloads/runtime - AI agent loads Qwen model IDs from Hugging Face model identifiers.
  - Implementation: `ai_agent_service/src/core/config.py` and `ai_agent_service/src/core/engine.py`.
  - SDK/Client: `vllm`, `transformers`, `Qwen2VLForConditionalGeneration`, `AutoProcessor`.
  - Auth: No Hugging Face token variable detected in `ai_agent_service/src/core/config.py`.

**OCR & Forecast Services:**
- Deep Learning service - Main app proxies invoice detection and forecasting to a local or remote DL service.
  - Implementation: `core/services/dl_client.py`, `routes/dl_routes.py`, `dl_service/model_app.py`, `dl_service/api/model1_routes.py`, and `dl_service/api/model2_routes.py`.
  - SDK/Client: Local Python imports by default; remote mode uses `requests`.
  - Auth: `DL_SERVICE_URL` and `DL_SERVICE_TIMEOUT`; no auth header detected in `core/services/dl_client.py`.
- Brain VLM OCR endpoint - DL OCR attempts `${HF_BASE_URL}/ocr` before local OCR fallbacks.
  - Implementation: `dl_service/services/ocr_service.py`.
  - SDK/Client: `requests`.
  - Auth: `HF_BASE_URL`; no token header detected for `/ocr` in `dl_service/services/ocr_service.py`.

**Workflow Webhooks:**
- Make/custom webhook, Slack webhook, Discord webhook - Workflow nodes send user-configured HTTP requests.
  - Implementation: `core/make_integration.py` and node handling in `core/workflow_engine.py`.
  - SDK/Client: `requests`.
  - Auth: User-provided webhook URLs in workflow node config; no separate secret variable detected.

**Search & Public Data:**
- DuckDuckGo Search - AI agent retrieves market/search snippets.
  - Implementation: `ai_agent_service/src/core/external_data.py` and `ai_agent_service/src/agents/researcher.py`.
  - SDK/Client: `duckduckgo-search` / `DDGS`.
  - Auth: None detected.
- Open-Meteo - AI agent fetches weather forecasts.
  - Implementation: `ai_agent_service/src/core/external_data.py`.
  - SDK/Client: `requests`.
  - Auth: None detected.

**Archive/Offline AI Tools:**
- DeepSeek/OpenAI-compatible APIs - Archive dataset refinement tools instantiate the OpenAI client against DeepSeek endpoints.
  - Implementation: `ai_agent_service/src/archive/tools/refine_knowledge.py`, `ai_agent_service/src/archive/tools/refine_charts.py`, and `ai_agent_service/src/archive/tools/smart_filter.py`.
  - SDK/Client: `openai` import detected in archive scripts; `openai` is not declared in `ai_agent_service/requirements.txt`.
  - Auth: Script-local API key handling detected by imports/search; no runtime env var documented in `README.md`.

**Frontend CDNs:**
- Bootstrap, Axios, Marked, Chart.js, Font Awesome, Google Fonts - UI dependencies load from jsDelivr, cdnjs, and Google Fonts.
  - Implementation: `ui/templates/base.html`, `ui/templates/admin_analytics.html`, and `templates/index.html`.
  - SDK/Client: Browser scripts/stylesheets.
  - Auth: None.

## Data Storage

**Databases:**
- Main application database - SQLite by default, optional PostgreSQL/Neon.
  - Connection: `DATABASE_PATH`, `POSTGRES_URL`, `USE_POSTGRES` in `core/config.py`.
  - Client: `sqlite3` and `psycopg2.pool.ThreadedConnectionPool` in `core/db/connection.py`; Alembic/SQLAlchemy migration connection in `migrations/env.py`.
  - Migration helper: `package/migrate_to_postgres.py` migrates SQLite rows to PostgreSQL and references `secrets/database.json`.
- DL service database - SQLite invoice/forecast history.
  - Connection: `dl_service/database/invoices.db` derived in `dl_service/utils/database.py`.
  - Client: `sqlite3` in `dl_service/utils/database.py`.
- AI agent memory database - SQLAlchemy connection with Postgres-compatible URLs or in-memory SQLite fallback.
  - Connection: `DATABASE_URL` in `ai_agent_service/src/core/config.py`.
  - Client: `SQLAlchemy` in `ai_agent_service/src/core/memory.py` and `ai_agent_service/src/core/saas_api.py`.
- Vector database - Persistent Chroma vector store for agent RAG.
  - Connection: `./data/vector_db` default in `ai_agent_service/src/core/knowledge.py`; repo data is present under `ai_agent_service/data/vector_db/`.
  - Client: `chromadb.PersistentClient` in `ai_agent_service/src/core/knowledge.py`.

**File Storage:**
- Local uploads - Main app writes workflow uploads under `uploads/` through `routes/workflow_routes.py`.
- DL uploads/models/data - DL paths are configured in `dl_service/config.py` for `dl_service/uploads/`, `dl_service/saved_models/`, and `dl_service/data/`.
- AI job state - Chat jobs are stored as JSON files under `jobs/` by `routes/ai_routes.py`.
- AI agent datasets and workflows - Local files live in `ai_agent_service/src/data/` and `ai_agent_service/my_workflows/`.
- Secrets/config files - `secrets/` exists and contains integration credential files; contents were not read.

**Caching:**
- Google Analytics cache - `core/services/analytics_service.py` reads and writes `secrets/ga_cache.json`; `routes/operations_routes.py` can clear it.
- Chroma persistence - `ai_agent_service/src/core/knowledge.py` persists vector data in `ai_agent_service/data/vector_db/`.
- Redis or distributed cache: Not detected in `package/requirements.txt`, `core/`, `routes/`, or `ai_agent_service/`.

## Authentication & Identity

**Auth Provider:**
- Custom email/password auth plus Google OAuth.
  - Implementation: Password auth in `core/auth.py`; Flask-Login setup in `core/extensions.py` and `app.py`; Google OAuth in `app.py` and `routes/google_routes.py`.
  - Password hashing: `bcrypt` in `core/auth.py`; legacy SHA-256 migration-on-login logic also exists in `core/auth.py`.
  - Session auth: Flask session and Flask-Login cookies configured in `app.py`.
  - OAuth scopes: Drive, Sheets, Docs, Gmail, and Analytics scopes are registered in `app.py`.

## Monitoring & Observability

**Error Tracking:**
- External error tracking: None detected in `package/requirements.txt`, `requirements-dev.txt`, `core/`, or `routes/`.

**Logs:**
- App logging helper - `core/logger.py` defines structured logging utilities for main app modules.
- DL logging helper - `dl_service/utils/logger.py` is used by DL API routes such as `dl_service/api/model1_routes.py`.
- Console output - `app.py`, `routes/ai_routes.py`, `core/services/analytics_service.py`, and AI agent modules emit `print()` output for runtime status.

## CI/CD & Deployment

**Hosting:**
- Not detected in repo config. No `Dockerfile`, `Procfile`, `runtime.txt`, or platform-specific deployment manifest was found.
- Main app expects local Flask execution from `app.py`; DL service expects local Flask execution from `dl_service/model_app.py`; AI service expects Uvicorn/ngrok execution from `ai_agent_service/launch_demo.py` and `ai_agent_service/src/server.py`.

**CI Pipeline:**
- None detected. `.github/` contains repository metadata and GSD assets, but `.github/workflows/` was not detected.

## Environment Configuration

**Required env vars:**
- `SECRET_KEY` - Main Flask secret in `app.py` and `core/config.py`; production raises when the default sentinel is used.
- `FLASK_ENV` - Enables development OAuth transport behavior in `app.py` and is documented in `README.md`.
- `POSTGRES_URL` - PostgreSQL/Neon database URL in `core/config.py`, `migrations/env.py`, and `package/migrate_to_postgres.py`.
- `USE_POSTGRES` - Forces PostgreSQL mode in `core/config.py`.
- `DATABASE_PATH` - SQLite database path in `core/config.py`.
- `DATABASE_URL` - AI agent SQLAlchemy DB URL in `ai_agent_service/src/core/config.py`.
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - Google OAuth credentials in `app.py`, `core/google_integration.py`, and `README.md`.
- `GA_PROPERTY_ID`, `GA_CACHE_LIFETIME_SECONDS` - Google Analytics config in `core/config.py` and `core/services/analytics_service.py`.
- `HF_BASE_URL`, `HF_TOKEN` - AI chat/upload service config in `routes/ai_routes.py`; `HF_BASE_URL` also configures OCR brain fallback in `dl_service/services/ocr_service.py`.
- `DL_SERVICE_URL`, `DL_SERVICE_TIMEOUT` - Remote DL service config in `core/services/dl_client.py`.
- `SITE_DOMAIN`, `BASE_URL` - Public URL/domain values in `core/config.py` and template context in `app.py`.
- `LAYOUT_WEIGHTS_PATH`, `LAYOUT_INFER_DEVICE` - Layout detector config in `dl_service/config.py`.
- `PADDLE_OCR_USE_GPU`, `PADDLE_OCR_DEVICE`, `PADDLE_OCR_LANG` - PaddleOCR config in `dl_service/services/ocr_service.py`.

**Secrets location:**
- `.env` and `.env.example` exist at repo root and were not read.
- `secrets/analytics_service_account.json` - Google Analytics service account path referenced in `core/config.py` and `core/services/analytics_service.py`.
- `secrets/google_oauth.json` - OAuth client fallback referenced in `core/google_integration.py`.
- `secrets/token.json` and `secrets/token adminmail.json` - Google OAuth token paths referenced in `core/google_integration.py`.
- `secrets/database.json` - PostgreSQL URL fallback referenced in `package/migrate_to_postgres.py`.
- `secrets/ga_cache.json` - Analytics cache referenced in `core/services/analytics_service.py` and `routes/operations_routes.py`.

## Webhooks & Callbacks

**Incoming:**
- Google OAuth callback - `/auth/google/callback` in `routes/google_routes.py`.
- Internal workflow execution - `/api/workflow/execute` in `routes/workflow_routes.py` executes saved workflow graph data.
- Public webhook receiver: Not detected. `webhook_trigger` appears as a workflow node type in `static/js/workspace_builder.js`, but no Flask route accepts third-party webhook callbacks.

**Outgoing:**
- Make/custom webhooks - `core/workflow_engine.py` invokes `core/make_integration.py` for `make_webhook` nodes.
- Slack webhooks - `core/workflow_engine.py` sends text payloads for `slack_notify` nodes.
- Discord webhooks - `core/workflow_engine.py` sends content payloads for `discord_notify` nodes.
- Google API callbacks/requests - `core/google_integration.py` calls Drive, Sheets, Docs, Gmail, and GA APIs.
- AI/DL HTTP calls - `routes/ai_routes.py`, `core/services/dl_client.py`, and `dl_service/services/ocr_service.py` call configured AI/DL service URLs.

---

*Integration audit: 2026-06-08*
