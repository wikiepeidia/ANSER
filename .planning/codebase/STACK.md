# Technology Stack

**Analysis Date:** 2026-07-08

## Languages

**Primary:**
- Python 3.13 - Main Flask web app (`app.py`), core services (`core/`), routes (`routes/`), AI agent service (`ai_agent_service/`), deep learning service (`dl_service/`)

**Secondary:**
- JavaScript - Frontend interactivity, `static/`, `ui/templates/`
- HTML/Jinja2 - Templates in `templates/` and `ui/templates/`
- CSS - `static/`
- SQL - Migrations in `migrations/`

## Runtime

**Environment:**
- Python 3.13.13 (local dev interpreter observed)
- Node.js v24.14.0 present (used for `package.json` tooling / n8n workflows, not app runtime)

**Package Manager:**
- pip, with split requirement files:
  - `requirements.txt` - entry point, includes `requirements-base.txt`
  - `requirements-base.txt` - core Flask app dependencies
  - `requirements-ml.txt` - ML/DL dependencies (torch, tensorflow, transformers, OCR)
  - `requirements-dev.txt` - dev/test tooling (pytest, ruff)
  - `ai_agent_service/requirements.txt` - separate deps for the AI agent microservice (vllm, fastapi, qwen_vl_utils)
- npm - `package.json` present at repo root (currently empty `{}` — no declared npm dependencies; likely placeholder or reserved for future tooling)
- Lockfile: `package-lock.json` present; no Python lockfile (uses versioned `requirements-*.txt` instead)

## Frameworks

**Core:**
- Flask >=3.0,<4.0 - main web app (`app.py`)
- Flask-Login >=0.6.3 - session/user auth
- Flask-WTF >=1.2.1 - forms/CSRF
- Flask-Talisman >=1.1.0 - security headers/CSP (`app.py`)
- Flask-Limiter >=3.5.0 - rate limiting
- FastAPI + uvicorn - used in `ai_agent_service/` (`ai_agent_service/server.py`) and `dl_service/model_app.py`
- Authlib - OAuth client (`app.py`, Google OAuth flow)

**Testing:**
- pytest >=8.0.0 with `pytest-cov`, `pytest-mock`, `pytest-timeout` (config: `pytest.ini`, tests in `tests/`)
- ruff >=0.4.0 - linting

**Build/Dev:**
- python-dotenv - loads `.env` (called in `app.py`, `core/config.py`, `dl_service/config.py`)
- Alembic - DB migrations (`alembic.ini`, `migrations/`)

## Key Dependencies

**Critical:**
- SQLAlchemy >=2.0 - ORM, database access layer (`core/database.py`, `core/models.py`)
- psycopg / psycopg2-binary - PostgreSQL driver
- redis >=5.0.0 + rq >=1.16.0 - async task queue (background jobs, workers — see `worker.py`)
- torch, tensorflow, transformers - deep learning models (`dl_service/`)
- easyocr, pytesseract, paddleocr, paddlepaddle, ultralytics - OCR and vision pipeline (`dl_service/`)
- chromadb, sentence-transformers - RAG/vector search (`ai_agent_service/`, `requirements-ml.txt`)
- vllm - local LLM inference server used by `ai_agent_service/`

**Infrastructure:**
- google-auth-oauthlib, google-api-python-client, google-analytics-data - Google integrations (`core/google_integration.py`)
- authlib, oauthlib - OAuth2 flows
- passlib[bcrypt] - password hashing
- gdown - Google Drive downloads

## Configuration

**Environment:**
- `.env` (present, git-ignored) and `.env.example` (template) loaded via `python-dotenv` at startup in `app.py`, `core/config.py`, `dl_service/config.py`
- Centralized config class: `core/config.py` (`Config`) reads env vars for `SECRET_KEY`, `DATABASE_PATH`, `POSTGRES_URL`, `REDIS_URL`, `SITE_DOMAIN`, `BASE_URL`, `N8N_PORT`, `GA_PROPERTY_ID`, etc.
- `dl_service/config.py` has its own config module for model paths (`LSTM_MODEL_PATH`, `LAYOUT_WEIGHTS_PATH`, etc.)
- Secrets directory: `secrets/` (git-ignored) holds service account JSON, e.g. `secrets/analytics_service_account.json` referenced by `GA_SERVICE_ACCOUNT_FILE` in `core/config.py`

**Build:**
- `pytest.ini` - test discovery config
- `alembic.ini` - migration config (DB URL resolved dynamically in `migrations/env.py`, not hardcoded)
- `docker-compose.yml` - defines only an `n8n` service (workflow automation container), not the main app

## Platform Requirements

**Development:**
- Windows (OneDrive-synced repo path observed) with Git Bash / PowerShell
- Python 3.13, pip, virtualenv recommended
- Optional: Docker for n8n workflow automation container (`docker-compose.yml`)

**Production:**
- Deployment target not explicitly declared in repo (no `Procfile`, `vercel.json`, or cloud config found)
- `wsgi.py` present, suggesting WSGI-server deployment (e.g. gunicorn/uWSGI) is expected for the Flask app
- PostgreSQL expected in production (`Config.POSTGRES_URL`, `Config.USE_POSTGRES`); falls back to SQLite file (`group_project_ai_ml.db`) for local/dev

---

*Stack analysis: 2026-07-08*
