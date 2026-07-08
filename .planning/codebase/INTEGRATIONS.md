# External Integrations

**Analysis Date:** 2026-07-08

## APIs & External Services

**Google Services:**
- Google OAuth2 (login, identity) - `app.py` (`_configure_oauth`), `core/google_integration.py`
  - Scopes requested: `openid email profile`, Drive (readonly + file), Sheets, Docs, Gmail send, Analytics readonly
  - SDK/Client: `authlib.integrations.flask_client.OAuth`, `google-auth-oauthlib`, `google-api-python-client`
  - Auth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` env vars
- Google Analytics Data API - `core/google_integration.py`, config in `core/config.py` (`GA_PROPERTY_ID`, `GA_CACHE_LIFETIME_SECONDS`)
  - Auth: service account file at `secrets/analytics_service_account.json` (`GA_SERVICE_ACCOUNT_FILE`), sets `GOOGLE_APPLICATION_CREDENTIALS` env var at runtime

**Workflow Automation:**
- n8n (self-hosted, via Docker) - `docker-compose.yml`
  - Runs as container `anser-n8n`, exposed on `N8N_PORT` (default 5680)
  - App connects via `N8N_ORIGIN = http://localhost:{N8N_PORT}` (`core/config.py`)
  - Used by `core/automation_engine.py` / `core/workflow_engine.py` for workflow execution

**Outbound Webhooks (Make.com and generic):**
- Generic webhook trigger utility - `core/make_integration.py` (`trigger_webhook`)
  - Validates destination via `validate_public_webhook_url` (`core/security.py`) to block SSRF to private/internal hosts
  - Sends POST/GET via `requests` with 5s timeout, `allow_redirects=False`

**LLM / AI Inference:**
- Local LLM inference server via vllm - `ai_agent_service/` (`ai_agent_service/requirements.txt`: `vllm`, `fastapi`, `uvicorn`)
- Qwen2-VL vision-language model tooling - `qwen_vl_utils`, `decord` (`ai_agent_service/requirements.txt`)
- No hosted third-party LLM API keys (OpenAI/Anthropic/Gemini) detected in `ai_agent_service/` config or core code — inference appears self-hosted via vllm

**Search:**
- DuckDuckGo search - `duckduckgo-search` (`ai_agent_service/requirements.txt`), `ddgs` (`requirements-ml.txt`)

## Data Storage

**Databases:**
- PostgreSQL (primary, production) - `core/database.py`
  - Connection: `POSTGRES_URL` env var (normalizes `postgres://` → `postgresql://`)
  - Client/ORM: SQLAlchemy >=2.0, `psycopg[binary]` / `psycopg2-binary`
  - Migrations: Alembic (`alembic.ini`, `migrations/`), DB URL resolved dynamically in `migrations/env.py` from `Config`
- SQLite (local/dev fallback) - `DATABASE_PATH` env var, default `group_project_ai_ml.db` (present in repo root as a local dev artifact); also `database.db` present
- Additional DB-related code under `core/db/` and `database/`

**File Storage:**
- Local filesystem only - `uploads/` directory (referenced in `dl_service/config.py` as `UPLOAD_DIR`), `dl_service/uploads/`
- No cloud object storage (S3/GCS/Azure Blob) integration detected

**Caching:**
- Redis - `REDIS_URL` env var (default `redis://localhost:6379/0`), used for async task queue via `rq` (see `worker.py`, `Config.ALLOW_AI_QUEUE_WITHOUT_WORKER`)
- In-app caching: `GA_ENABLE_CACHING` / `GA_CACHE_LIFETIME_SECONDS` for Google Analytics responses (`core/config.py`)

## Authentication & Identity

**Auth Provider:**
- Custom session-based auth via Flask-Login (`core/auth.py`, `core/extensions.py`) backed by `core/models.py` (`User` model)
- Google OAuth2 as an additional/linked identity provider (`app.py`, `core/google_integration.py`)
- Password hashing via `passlib[bcrypt]`

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry/Rollbar/Bugsnag dependency found)

**Logs:**
- Custom logger module: `core/logger.py` (`get_logger`), used throughout `app.py` and services
- Log output directory: `logs/`
- `ai_agent_service/api_log.txt` - service-specific log file

## CI/CD & Deployment

**Hosting:**
- Not explicitly declared in repo (no Vercel/Heroku/Fly/Render config detected)
- `wsgi.py` present implies a WSGI server (gunicorn/uWSGI) fronts `app.py` in production
- Site domain configurable via `SITE_DOMAIN` env var, default `auto-flowai.com` (`core/config.py`)

**CI Pipeline:**
- Not detected in this scan (no `.github/workflows/` CI files found for build/test automation; only `.github/skills`, `.github/agents`, `.github/get-shit-done/` for GSD tooling per `CLAUDE.md`)

## Environment Configuration

**Required env vars (observed across `core/config.py`, `app.py`, `core/database.py`, `dl_service/config.py`):**
- `SECRET_KEY` - Flask session secret (required in production, raises `RuntimeError` if left at default)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - Google OAuth
- `POSTGRES_URL` / `USE_POSTGRES` - database connection
- `DATABASE_PATH` - SQLite fallback path
- `REDIS_URL` - Redis/queue connection
- `ALLOW_AI_QUEUE_WITHOUT_WORKER` - dev convenience flag for async AI jobs
- `SITE_DOMAIN`, `BASE_URL` - public site URLs
- `N8N_PORT` - n8n container port
- `GA_PROPERTY_ID`, `GA_CACHE_LIFETIME_SECONDS` - Google Analytics
- `FLASK_ENV` / `APP_ENV` - environment mode switch (dev vs. production-safe defaults)
- `SESSION_COOKIE_SECURE`, `RATELIMIT_ENABLED`, `FORCE_HTTPS`, `STRICT_TRANSPORT_SECURITY` - security posture toggles (`app.py`, `core/security.py`)
- `MAX_CONTENT_LENGTH` - upload size limit
- `LAYOUT_WEIGHTS_PATH`, `LAYOUT_INFER_DEVICE` - DL model config (`dl_service/config.py`)

**Secrets location:**
- `.env` (git-ignored, local) with `.env.example` as template
- `secrets/` directory (git-ignored) for service account JSON credentials (e.g. `secrets/analytics_service_account.json`)
- `secrets.rar` archive present in repo root — flagged as existing but contents not inspected (should be verified it is git-ignored/not committed with real secrets)

## Webhooks & Callbacks

**Incoming:**
- Not explicitly identified in this scan; likely handled via `routes/` blueprints for OAuth callback (`/oauth/callback`-style Google redirect) — verify in `routes/`

**Outgoing:**
- Generic outbound webhook dispatch with SSRF protection - `core/make_integration.py` (`trigger_webhook`), destination validated by `core/security.py` (`validate_public_webhook_url`)
- n8n workflow webhooks - triggered via `N8N_ORIGIN` from `core/automation_engine.py` / `core/workflow_engine.py`

---

*Integration audit: 2026-07-08*
