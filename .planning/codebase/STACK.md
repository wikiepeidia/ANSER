# Technology Stack

**Analysis Date:** 2026-06-08

## Languages

**Primary:**
- Python 3.10+ - Main Flask application in `app.py`, backend packages in `core/` and `routes/`, deep-learning service in `dl_service/`, and AI agent service in `ai_agent_service/src/`. The minimum version is documented in `README.md`.

**Secondary:**
- JavaScript - Browser scripts are served directly from `static/js/` and referenced by Jinja templates such as `ui/templates/base.html`; there is no frontend bundler in `package.json`.
- HTML/Jinja2 - Server-rendered UI templates live in `ui/templates/`; legacy templates also exist in `templates/`.
- CSS - Static styles live in `static/css/` and are loaded from templates such as `ui/templates/base.html`.
- SQL - Main schema creation uses raw SQL in `core/db/connection.py`; Alembic migrations use raw SQL in `migrations/`.
- JSON/JSONL/CSV - AI training data and workflow blueprints live in `ai_agent_service/src/data/`, `ai_agent_service/my_workflows/`, and `dl_service/data/`.

## Runtime

**Environment:**
- CPython 3.10+ - Required by `README.md`; no `.python-version`, `runtime.txt`, `Dockerfile`, or `Procfile` was detected.
- Flask development server - Main app runs from `app.py` on `127.0.0.1:5000`; the separate DL app runs from `dl_service/model_app.py` or `run_dl_service.py` on port `5001`.
- FastAPI/Uvicorn service - AI agent API is implemented in `ai_agent_service/src/server.py` and launched through Uvicorn/ngrok tooling in `ai_agent_service/launch_demo.py`.
- CUDA/GPU runtime for AI agent - `ai_agent_service/src/core/engine.py` loads `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` with vLLM and `Qwen/Qwen2-VL-7B-Instruct` with `device_map="cuda"`.

**Package Manager:**
- pip 23+ - Required by `README.md`; install automation is in `package/installer.py`.
- Lockfile: Python lockfile missing; dependencies are declared in `package/requirements.txt`, `requirements-dev.txt`, `ai_agent_service/requirements.txt`, and `ai_agent_service/src/requirements.txt`.
- npm metadata: `package.json` exists but contains `{}`; `package-lock.json` exists but there are no npm dependencies or scripts in `package.json`.

## Frameworks

**Core:**
- Flask `>=3.0,<4.0` - Main web app factory and blueprint registration in `app.py`; DL inference API in `dl_service/model_app.py`.
- Flask-Login `>=0.6.3,<0.7` - Session login manager initialized in `core/extensions.py` and callbacks registered in `app.py`.
- Flask-WTF `>=1.2.1,<1.3` - CSRF protection initialized in `core/extensions.py` and error handling in `app.py`.
- Flask-Talisman `>=1.1.0,<1.2` - CSP/security headers configured in `app.py`.
- Flask-Limiter `>=3.5.0,<3.6` - Limiter singleton in `core/extensions.py`; rate limits are configured in `app.py`.
- Authlib + OAuthlib - Google OAuth client setup in `app.py` and route handling in `routes/google_routes.py`.
- FastAPI + Uvicorn - AI agent service endpoints in `ai_agent_service/src/server.py`.
- SQLAlchemy + Alembic - Alembic environment in `migrations/env.py`; AI agent memory and SaaS data access in `ai_agent_service/src/core/memory.py` and `ai_agent_service/src/core/saas_api.py`.

**Testing:**
- pytest `>=8.0.0` - Test runner configured by `pytest.ini`.
- pytest-cov `>=5.0.0` - Coverage settings configured by `.coveragerc`.
- pytest-mock `>=3.14.0`, pytest-timeout `>=2.3.1`, requests-mock `>=1.12.1` - Dev dependencies in `requirements-dev.txt`.

**Build/Dev:**
- No frontend build step - Static JS/CSS is loaded directly from `static/` and CDN URLs in `ui/templates/base.html`.
- Alembic - PostgreSQL migrations configured by `alembic.ini` and `migrations/env.py`.
- pyngrok + nest_asyncio - AI agent demo connectivity tooling declared in `ai_agent_service/requirements.txt` and used by `ai_agent_service/launch_demo.py`.
- pip installer script - `package/installer.py` upgrades pip and installs `package/requirements.txt`.

## Key Dependencies

**Critical:**
- `requests` - Outbound HTTP for AI service calls in `routes/ai_routes.py`, webhooks in `core/make_integration.py`, DL remote calls in `core/services/dl_client.py`, and OCR brain fallback in `dl_service/services/ocr_service.py`.
- `google-api-python-client`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-analytics-data` - Google Drive/Sheets/Docs/Gmail/GA4 integration in `core/google_integration.py` and `core/services/analytics_service.py`.
- `authlib` - Google OAuth/OpenID client registration in `app.py`.
- `psycopg[binary]`, `psycopg2-binary`, `SQLAlchemy`, `alembic` - PostgreSQL/Neon support in `core/db/connection.py`, `migrations/env.py`, and `package/migrate_to_postgres.py`.
- `bcrypt` / `passlib[bcrypt]` - Password hashing and verification in `core/auth.py`; `README.md` also instructs installing `bcrypt`.
- `torch`, `tensorflow`, `transformers`, `vllm`, `accelerate`, `bitsandbytes`, `sentencepiece` - LLM and DL model runtime in `dl_service/` and `ai_agent_service/src/core/engine.py`.
- `ultralytics`, `opencv-python-headless`, `Pillow`, `paddleocr`, `easyocr`, `pytesseract` - Invoice layout/OCR stack in `dl_service/services/model_loader.py`, `dl_service/services/layout_service.py`, and `dl_service/services/ocr_service.py`.
- `chromadb`, `sentence-transformers` - RAG vector store and embeddings in `ai_agent_service/src/core/knowledge.py`.
- `numpy`, `pandas`, `openpyxl`, `scikit-learn` - Data processing and Excel parsing in `core/excel_parser.py`, `dl_service/`, and service modules.

**Infrastructure:**
- `python-dotenv` - Environment loading in `core/config.py` and `dl_service/config.py`.
- `Werkzeug` - ProxyFix and file utilities used in `app.py`, `routes/workflow_routes.py`, and DL routes.
- `Flask-Talisman` - CSP allows local app plus Google Analytics, jsDelivr, Google Fonts, and cdnjs in `app.py`.
- `gdown` - Model/data download dependency declared in `package/requirements.txt`.
- Browser CDN assets - Bootstrap 5.3.0, Axios, Marked, Font Awesome 6.4.0, Google Fonts, and Chart.js 4.4.0 are referenced in `ui/templates/base.html` and `ui/templates/admin_analytics.html`.

## Configuration

**Environment:**
- Main app config is loaded with `load_dotenv()` in `core/config.py` and direct `os.environ` access in `app.py`.
- DL service config is loaded with `load_dotenv()` in `dl_service/config.py`.
- AI agent config reads `DATABASE_URL` in `ai_agent_service/src/core/config.py`.
- `.env` and `.env.example` files are present at repo root; contents were not read because they are environment/secret files.
- Required or documented main-app variables: `FLASK_ENV`, `SECRET_KEY`, `POSTGRES_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `HF_BASE_URL`, `HF_TOKEN`, and `GA_PROPERTY_ID` in `README.md`.
- Additional main-app variables used by code: `DATABASE_PATH`, `USE_POSTGRES`, `SITE_DOMAIN`, `BASE_URL`, `GA_CACHE_LIFETIME_SECONDS`, `DL_SERVICE_URL`, and `DL_SERVICE_TIMEOUT` in `core/config.py`, `core/services/dl_client.py`, and `app.py`.
- DL/model variables: `LAYOUT_WEIGHTS_PATH`, `LAYOUT_INFER_DEVICE`, `PADDLE_OCR_USE_GPU`, `PADDLE_OCR_DEVICE`, `PADDLE_OCR_LANG`, `LAYOUT_STAGE_ENABLED`, `LAYOUT_REBUILD`, `LAYOUT_BASE_MODEL`, `LAYOUT_EPOCHS`, `LAYOUT_BATCH`, `LAYOUT_IMGSZ`, and `LAYOUT_DEVICE` in `dl_service/config.py`, `dl_service/services/ocr_service.py`, and `dl_service/train_cnn_models.py`.

**Build:**
- Dependency manifests: `package/requirements.txt`, `requirements-dev.txt`, `ai_agent_service/requirements.txt`, `ai_agent_service/src/requirements.txt`, and empty `package.json`.
- Test config: `pytest.ini` and `.coveragerc`.
- Database migration config: `alembic.ini`, `migrations/env.py`, and `migrations/versions/001_initial_schema.py`.
- App configuration modules: `core/config.py`, `dl_service/config.py`, and `ai_agent_service/src/core/config.py`.

## Platform Requirements

**Development:**
- Install runtime dependencies with `pip install -r package/requirements.txt` from `README.md` or `python package/installer.py` from `package/installer.py`.
- Install test dependencies with `pip install -r requirements-dev.txt` from `requirements-dev.txt`.
- Run the main app with `python app.py` as documented in `README.md`.
- Run the DL service with `python dl_service/model_app.py` or `python run_dl_service.py` as documented in `README.md` and implemented in `run_dl_service.py`.
- Run the AI agent service with FastAPI/Uvicorn from `ai_agent_service/src/server.py`; `ai_agent_service/launch_demo.py` adds ngrok exposure for the service.
- Native OCR/model prerequisites may be required for PaddleOCR, Tesseract, CUDA, TensorFlow, PyTorch, and vLLM based on `package/requirements.txt`, `ai_agent_service/requirements.txt`, and `dl_service/services/ocr_service.py`.

**Production:**
- Deployment target: Not detected in repo config; there is no `Dockerfile`, `Procfile`, `.github/workflows/`, or platform manifest.
- Database target: SQLite by default via `core/config.py`; PostgreSQL/Neon is enabled by `POSTGRES_URL` or `USE_POSTGRES` in `core/config.py`.
- Reverse proxy assumptions: `ProxyFix` is enabled in `app.py`; Talisman HTTPS and secure-cookie flags are disabled in `app.py` for local HTTP behavior.
- External model/API target: `HF_BASE_URL` points the main app to a Hugging Face Space, ngrok tunnel, or compatible FastAPI AI service as documented in `README.md` and used in `routes/ai_routes.py`.

---

*Stack analysis: 2026-06-08*
