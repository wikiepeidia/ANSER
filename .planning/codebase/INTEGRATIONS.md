# External Integrations

**Analysis Date:** 2026-05-16

## Google OAuth 2.0 (Sign-In & API Access)

**What it does:** Enables Google sign-in ("Login with Google") and grants per-user OAuth tokens for Drive, Sheets, Docs, Gmail, and Analytics. Tokens are stored in the `users.google_token` DB column and passed to Google API calls on each user request.

**Credential source:**
- `GOOGLE_CLIENT_ID` — env var, read in `app.py` (`_configure_oauth()`, line 31)
- `GOOGLE_CLIENT_SECRET` — env var, read in `app.py` (`_configure_oauth()`, line 32)

**SDK:** `authlib` (`OAuth` class) + `google-auth-oauthlib` for token refresh

**Code files:**
- `app.py` — OAuth client registered via `authlib.integrations.flask_client.OAuth`; client stored in `app.extensions['google']`
- `routes/google_routes.py` — Redirect (`/auth/login/google`), callback (`/auth/google/callback`), connect (`/auth/connect/google`)
- `core/google_integration.py` — `get_google_service()` builds per-user `google.oauth2.credentials.Credentials` from stored token; `_load_client_credentials()` also falls back to reading `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` from env

**Scopes requested:**
```
openid email profile
drive.readonly  drive.file
spreadsheets    documents
gmail.send      analytics.readonly
```

---

## Google Drive API (v3)

**What it does:** Lists and reads files from a user's Google Drive. Used as a workflow node source and for reading documents into the AI pipeline.

**Credential source:** Per-user OAuth token (stored in DB; see Google OAuth above). Falls back to `secrets/token adminmail.json` if present.

**SDK:** `google-api-python-client` (`build('drive', 'v3', ...)`)

**Code files:**
- `core/google_integration.py` — `list_files()`, `get_google_service('drive', 'v3', token_info)`
- `core/workflow_engine.py` — `read_sheet` / `read_doc` workflow nodes call `google_integration` functions

---

## Google Sheets API (v4)

**What it does:** Reads and writes spreadsheet data as workflow node inputs/outputs (e.g. importing sales data, writing forecast results).

**Credential source:** Per-user OAuth token.

**SDK:** `google-api-python-client` (`build('sheets', 'v4', ...)`)

**Code files:**
- `core/google_integration.py` — `read_sheet()`, `write_sheet()` with smart sheet-name auto-detection retry
- `core/workflow_engine.py` — `read_sheet` and `write_sheet` workflow node types

---

## Google Docs API (v1)

**What it does:** Reads document text and appends content to Google Docs as a workflow output step.

**Credential source:** Per-user OAuth token.

**SDK:** `google-api-python-client` (`build('docs', 'v1', ...)`)

**Code files:**
- `core/google_integration.py` — `read_doc()`, `write_doc()`
- `core/workflow_engine.py` — `read_doc` and `write_doc` node types

---

## Gmail API (v1)

**What it does:** Sends transactional emails (workflow notifications, welcome mail, report delivery) from an admin Gmail account.

**Credential source (two paths):**
1. Per-user OAuth token (for user-initiated sends via workflow)
2. `secrets/token adminmail.json` — pre-authorized OAuth token for the admin sender account; regenerated via `secrets/generate token for welcome mail.py`

**SDK:** `google-api-python-client` (`build('gmail', 'v1', ...)`)

**Code files:**
- `core/google_integration.py` — `send_email()`, `get_google_service('gmail', 'v1', token_info)`; prefers `ADMIN_TOKEN_FILE` when it exists (line 119)
- `core/workflow_engine.py` — `gmail_send` workflow node type

---

## Google Analytics 4 (Data API v1beta)

**What it does:** Fetches active users and page-view metrics for the admin analytics dashboard. Results are cached locally in `secrets/ga_cache.json` to reduce API calls.

**Credential source:**
- `secrets/analytics_service_account.json` — Google service account JSON key (cannot be flattened to env var); path set via `Config.GA_SERVICE_ACCOUNT_FILE`
- `GA_PROPERTY_ID` — numeric GA4 Property ID, env var (default `517047582` in `core/config.py`)
- `GA_CACHE_LIFETIME_SECONDS` — env var (default `3600`)

**SDK:** `google-analytics-data` (`BetaAnalyticsDataClient`)

**Code files:**
- `core/google_integration.py` — `get_analytics_report(property_id)` sets `GOOGLE_APPLICATION_CREDENTIALS` env var and calls `BetaAnalyticsDataClient`
- `core/services/analytics_service.py` — `AnalyticsService` class; instantiates `BetaAnalyticsDataClient` with `service_account.Credentials.from_service_account_file()`; includes cache and mock fallback
- `core/config.py` — `GA_PROPERTY_ID`, `GA_SERVICE_ACCOUNT_FILE`, `GA_ENABLE_CACHING`, `GA_CACHE_LIFETIME_SECONDS`

---

## HuggingFace / ngrok AI Agent Service

**What it does:** The main Flask app posts user chat messages to a remote AI agent endpoint (hosted on HuggingFace Spaces or exposed via ngrok). The agent processes the message and returns a text response. The connection uses Bearer token auth.

**Credential source:**
- `HF_BASE_URL` — base URL of the AI agent endpoint (e.g. `https://xxx.ngrok-free.dev`); read via `os.environ.get('HF_BASE_URL')`
- `HF_TOKEN` — HuggingFace API token for Bearer auth; read via `os.environ.get('HF_TOKEN')`

**Protocol:** HTTP POST to `{HF_BASE_URL}/chat` with JSON body `{user_id, store_id, message}`; header `Authorization: Bearer {HF_TOKEN}`, `ngrok-skip-browser-warning: true`

**Code files:**
- `routes/ai_routes.py` — `background_ai_task()` (lines 56–76) builds the request and posts to `HF_BASE_URL/chat`
- `dl_service/services/ocr_service.py` — `_get_brain_url()` reads `HF_BASE_URL` to optionally offload OCR interpretation to the AI agent

---

## Neon / PostgreSQL (Cloud Database)

**What it does:** Production database backend. When `POSTGRES_URL` is set, the app connects to a managed PostgreSQL instance (Neon recommended) instead of the local SQLite file.

**Credential source:**
- `POSTGRES_URL` — full connection string (e.g. `postgresql://user:pass@host/db?sslmode=require`); read in `core/config.py` line 16

**Driver:** `psycopg2` (`psycopg2.connect(Config.POSTGRES_URL)`)

**Code files:**
- `core/config.py` — `POSTGRES_URL`, `USE_POSTGRES` derived flag
- `core/database.py` — `Database.get_connection()` (line 96): branches on `self.use_postgres`; uses `PGShimCursor`/`PGShimConnection` to normalize `?` → `%s` and inject `RETURNING id` for INSERT last-row-id
- `core/extensions.py` — `db_manager = Database()` singleton used throughout

**SQLite fallback:** `group_project_ai_ml.db` (project root); used when `POSTGRES_URL` is absent.

---

## Make.com / Generic Webhooks

**What it does:** Workflow engine node that triggers arbitrary HTTP webhooks (Make.com scenarios, custom APIs) with configurable method and JSON payload.

**Credential source:** Webhook URLs are stored per-workflow in the database (user-configured in the workflow canvas UI). No dedicated env var.

**Code files:**
- `core/make_integration.py` — `trigger_webhook(url, method, payload)` — raw `requests.post/get`
- `core/workflow_engine.py` — `make_webhook` node type (line 267), `slack_notify` node (line 290), `discord_notify` node (line 316); all call `trigger_webhook()`

---

## Slack Webhook Integration

**What it does:** Workflow node that sends a message to a Slack channel via an Incoming Webhook URL.

**Credential source:** Webhook URL stored per-workflow in DB (user-configured). No dedicated env var.

**Code files:**
- `core/workflow_engine.py` — `slack_notify` node type (lines 290–314); calls `trigger_webhook(url, "POST", {"text": message})`

---

## Discord Webhook Integration

**What it does:** Workflow node that sends a message to a Discord channel via a Webhook URL.

**Credential source:** Webhook URL stored per-workflow in DB (user-configured). No dedicated env var.

**Code files:**
- `core/workflow_engine.py` — `discord_notify` node type (lines 316–340); calls `trigger_webhook(url, "POST", {"content": message})`

---

## Deep Learning Service (Internal Microservice)

**What it does:** Separate Flask process running on port 5001 that exposes OCR, invoice detection (YOLO + PaddleOCR), and LSTM sales forecasting endpoints. The main app communicates with it via `DLClient`.

**Credential source:**
- `DL_SERVICE_URL` — env var (default `http://localhost:5001`)
- `DL_SERVICE_TIMEOUT` — env var (default `30` seconds)
- `LAYOUT_WEIGHTS_PATH` — env var override for YOLO weights path
- `LAYOUT_INFER_DEVICE` — env var (`cpu`/`cuda`/`auto`)

**Code files:**
- `core/services/dl_client.py` — `DLClient` class; local-import path (direct Python imports) or remote HTTP path
- `dl_service/model_app.py` — Flask app serving `/api/model1/detect`, `/api/model2/forecast`, `/api/ocr/`, `/api/history`
- `dl_service/config.py` — reads `LAYOUT_WEIGHTS_PATH`, `LAYOUT_INFER_DEVICE` from env
- `run_dl_service.py` — process launcher for the DL service

---

## Environment Configuration Summary

**File to copy and fill:** `.env.example` → `.env` (gitignored)

| Env Var | Service | Required |
|---------|---------|----------|
| `POSTGRES_URL` | Neon PostgreSQL | No (SQLite fallback) |
| `GOOGLE_CLIENT_ID` | Google OAuth | Yes for OAuth login |
| `GOOGLE_CLIENT_SECRET` | Google OAuth | Yes for OAuth login |
| `HF_BASE_URL` | AI Agent (HuggingFace/ngrok) | Yes for AI chat |
| `HF_TOKEN` | AI Agent | Yes if endpoint is protected |
| `SECRET_KEY` | Flask sessions | Yes (always set in prod) |
| `GA_PROPERTY_ID` | Google Analytics 4 | No (has default) |
| `GA_CACHE_LIFETIME_SECONDS` | Google Analytics 4 | No (default 3600) |
| `DL_SERVICE_URL` | DL microservice | No (default localhost:5001) |
| `DL_SERVICE_TIMEOUT` | DL microservice | No (default 30s) |
| `LAYOUT_WEIGHTS_PATH` | YOLO layout detector | No (default path in dl_service) |
| `LAYOUT_INFER_DEVICE` | YOLO inference | No (default auto) |

**JSON files still required in `secrets/`:**
| File | Service | Notes |
|------|---------|-------|
| `secrets/analytics_service_account.json` | Google Analytics 4 | Service account key; not committable |
| `secrets/token adminmail.json` | Gmail (admin sender) | OAuth token; regenerate via `secrets/generate token for welcome mail.py` |

---

*Integration audit: 2026-05-16*
