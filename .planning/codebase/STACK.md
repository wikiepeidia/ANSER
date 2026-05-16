# Technology Stack

**Analysis Date:** 2026-05-16

## Languages

**Primary:**
- Python 3.x - Core backend, AI/ML services, workflow engine, all route handlers
- JavaScript (ES6+) - Frontend behavior in `static/js/` (admin panels, workflow canvas, product management)
- HTML/CSS (Jinja2) - Server-rendered templates in `ui/templates/`

**Secondary:**
- JSON - Configuration, workflow definitions, secrets (two remaining JSON credential files)

## Runtime

**Environment:**
- Python 3.x (no explicit lock; `.nvmrc` not present)
- Flask WSGI via Werkzeug for the main app
- Second Flask process for the deep learning service (port 5001, `dl_service/model_app.py`)

**Package Manager:**
- pip with `package/requirements.txt` (main) and `requirements-dev.txt` (test tooling)
- No lockfile — direct requirements.txt only
- npm present (`package.json`) but empty (no JS build pipeline)

## Frameworks

**Web:**
- Flask `>=3.0,<4.0` — Main application factory in `app.py`; blueprints for every feature area
- Werkzeug — WSGI middleware (`ProxyFix`) and request/response utilities
- Flask-Login `>=0.6.3,<0.7` — Session management and `@login_required` decorator
- Flask-WTF `>=1.2.1,<1.3` — CSRF protection via `CSRFProtect`
- Flask-Talisman `>=1.1.0,<1.2` — Security headers (HSTS, CSP, frame-ancestors)
- Flask-Limiter `>=3.5.0,<3.6` — Rate limiting (currently disabled in dev: `RATELIMIT_ENABLED=False`)
- authlib `1.x` — OAuth2 client for Google sign-in (`app.py`, `routes/google_routes.py`)

**Deep Learning / AI:**
- PyTorch (`torch`) — Core tensor framework; used by VietOCR and Florence-2 vision model
- TensorFlow — LSTM forecasting model (`dl_service/saved_models/import_forecast_lstm.weights.h5`)
- transformers `4.46.0+` — HuggingFace model loading; vision-language tasks
- ultralytics (YOLO) — Layout detection for invoice processing (`dl_service/services/layout_service.py`)
- PaddleOCR `>=2.6.0` + PaddlePaddle `>=2.4.0` — Vietnamese OCR pipeline (`dl_service/services/cpt_ocr.py`)
- EasyOCR — Fallback OCR engine (`dl_service/services/ocr_service.py`)
- pytesseract — Tesseract wrapper (fallback OCR path)
- timm — PyTorch Image Models for Florence-2 vision components
- einops — Tensor manipulation for vision transformers
- sentence-transformers — Semantic embeddings
- sentencepiece — Tokenizer support for transformer models
- chromadb — Vector database for RAG (`ai_agent_service/`)
- accelerate `>=1.0.0` — Distributed/quantized model loading
- bitsandbytes `>=0.44.1` — 4/8-bit quantization

**Data / Numerical:**
- numpy `>=1.21.0`
- pandas — Data manipulation; LSTM training datasets
- scikit-learn — Preprocessing and evaluation metrics
- openpyxl — Excel read/write support

**Computer Vision:**
- opencv-python-headless `>=4.5.0` — Image preprocessing pipeline
- Pillow — Image loading and conversion

**Document Parsing:**
- pypdf — PDF text extraction
- python-docx — Word document parsing
- pdf2image — PDF-to-image for OCR preprocessing

**Database:**
- SQLAlchemy `>=2.0` — ORM layer (used in `database/progres.py`); direct psycopg2 used in `core/database.py`
- psycopg2-binary + psycopg[binary] — PostgreSQL drivers
- alembic — Database migrations
- sqlite3 (stdlib) — Default local database

**Authentication / OAuth:**
- passlib[bcrypt] — Password hashing (`core/auth.py`)
- google-auth-oauthlib — Google OAuth2 flow
- google-auth-httplib2 — HTTP transport for Google auth
- google-api-python-client — Google Drive, Sheets, Docs, Gmail API clients
- google-analytics-data — GA4 Data API v1beta (`BetaAnalyticsDataClient`)

**Utilities:**
- python-dotenv — `.env` file loading; called in `core/config.py` and `dl_service/config.py`
- requests — HTTP client for HuggingFace/ngrok AI agent calls and webhook dispatch
- pytz — Timezone handling
- lunardate — Lunar calendar calculations
- addict / easydict — Attribute-accessible dictionaries
- ddgs — DuckDuckGo search API
- gdown — Google Drive file download (model weights)

**Testing:**
- pytest `>=8.0.0` — Test runner; config in `pytest.ini`
- pytest-cov `>=5.0.0` — Coverage reporting
- pytest-mock `>=3.14.0` — Mocking support
- pytest-timeout `>=2.3.1` — Test timeouts
- requests-mock `>=1.12.1` — HTTP request mocking

## Key Dependencies

**Critical (app won't start without):**
- Flask `>=3.0` — Entire web layer
- python-dotenv — Credentials are loaded from `.env` at startup via `core/config.py`
- passlib[bcrypt] — Password verification on every login
- Flask-Login / Flask-WTF / Flask-Talisman — Security baseline

**Infrastructure:**
- psycopg2-binary — Required when `POSTGRES_URL` is set (Neon cloud DB)
- torch / tensorflow — Required for invoice detection and LSTM forecasting in `dl_service/`
- google-api-python-client — Required for all Google API integrations

## Configuration

**Environment:**
- Primary mechanism: `.env` file at project root, loaded by `python-dotenv` in `core/config.py` (line 4: `load_dotenv()`) and `dl_service/config.py` (line 8: `load_dotenv()`)
- Template committed to repo: `.env.example`
- Actual `.env` file is gitignored (contains real secrets)

**Key env vars (from `.env.example`):**
```
POSTGRES_URL          # Neon PostgreSQL connection string
GOOGLE_CLIENT_ID      # Google OAuth2 client ID
GOOGLE_CLIENT_SECRET  # Google OAuth2 client secret
HF_BASE_URL           # HuggingFace/ngrok AI agent endpoint
HF_TOKEN              # HuggingFace API bearer token
SECRET_KEY            # Flask session signing key
GA_PROPERTY_ID        # Google Analytics 4 Property ID (numeric)
```

**Remaining JSON credential files (cannot be env vars):**
- `secrets/analytics_service_account.json` — Google service account for GA4 Data API
- `secrets/token adminmail.json` — Gmail OAuth token for the admin sender account (regenerate via `secrets/generate token for welcome mail.py`)

**Derived config class:** `core/config.py` — `Config` class reads all vars via `os.environ.get()`; `dl_service/config.py` reads model path overrides.

**Build:**
- No build step — Flask runs directly via `python app.py` (port 5000) or `python run_dl_service.py` (DL service port 5001)

## Platform Requirements

**Development:**
- Python 3.x with pip
- GPU optional (CPU inference supported with fallback paths)
- Windows supported (explicit UTF-8 reconfigure in `dl_service/model_app.py`; PaddlePaddle PIR workaround in `dl_service/services/ocr_service.py`)

**Production:**
- Linux server recommended (Ubuntu/Debian) for ML library compatibility
- PostgreSQL (Neon or Railway) when `POSTGRES_URL` is set
- Reverse proxy (Nginx) for SSL termination — app uses `ProxyFix` middleware
- Process manager (Gunicorn/uWSGI) for production WSGI

---

*Stack analysis: 2026-05-16*
