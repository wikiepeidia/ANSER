# Codebase Concerns

**Analysis Date:** 2026-05-16

---

## CRITICAL

### Missing Module-Level Attributes Referenced by Routes

- Issue: `routes/workflow_routes.py` calls `app_module.db`, `app_module.workflow_service`, and `app_module.current_user`. `routes/ai_routes.py` calls `app_module.ai_chat_service`. None of these attributes exist at module level in `app.py`.
- Files: `routes/workflow_routes.py` (lines 27, 28, 44, 45, 60, 61, 76, 77, 95), `routes/ai_routes.py` (lines 159, 166, 171, 182, 196, 212), `routes/inventory_routes.py` (lines 49, 52, 124, 129, 131)
- Impact: The GET `/api/workflows`, POST `/api/workflows`, DELETE `/api/workflows/<id>`, workflow execute, and all AI chat routes will raise `AttributeError` at runtime and return 500 errors. This breaks the primary demo features (workflow builder, AI chat).
- Fix approach: Either export these names from `app.py` as module-level attributes (`db = db_manager`, `workflow_service = ...`, etc.) or refactor routes to use `current_app.extensions` (already used correctly in other blueprints).

---

### Password Hashing Inconsistency (SHA-256 vs Werkzeug Bcrypt)

- Issue: `core/auth.py` and `core/database.py` hash passwords with `hashlib.sha256()` (no salt). `core/services/user_service.py` uses `werkzeug.security.generate_password_hash` (bcrypt). `routes/google_routes.py` uses `werkzeug.security.generate_password_hash` for Google-created accounts. Users created via `AuthManager.register_user()` use SHA-256; the reset-password path uses bcrypt. These two hashing schemes are incompatible.
- Files: `core/auth.py` (lines 11-12, 46), `core/database.py` (line 370), `core/services/user_service.py` (line 127), `routes/google_routes.py` (line 93)
- Impact: Users whose passwords have been reset via the admin panel cannot log in because `verify_user()` checks SHA-256 but the stored hash is bcrypt. Demo accounts reset before the jury presentation will be locked out.
- Fix approach: Standardize on `werkzeug.security.generate_password_hash` / `check_password_hash` everywhere. Migrate `verify_user` in `core/auth.py` to use `check_password_hash`. Run a one-time migration to rehash existing SHA-256 passwords.

---

### `eval()` on Workflow Template Strings (Code Injection Risk)

- Issue: `core/workflow_engine.py` uses Python's built-in `eval()` to resolve `{{nodeId.path}}` template expressions from workflow JSON data stored in the database and supplied by users.
- Files: `core/workflow_engine.py` (lines 28, 64)
- Impact: Any authenticated user can craft a workflow payload that executes arbitrary Python code on the server. Even a comment in the code notes this is "DANGEROUS in prod, okay for test PoC".
- Fix approach: Replace `eval()` with a safe path-traversal implementation. Use `jmespath`, recursive dict/list access by key/index, or Jinja2 with a sandbox. The `{{node.key[0]}}` syntax can be resolved without `eval`.

---

### Rate Limiting Permanently Disabled in Production Config

- Issue: `app.py` line 74 sets `flask_app.config['RATELIMIT_ENABLED'] = False` unconditionally in `create_app()`. There is no environment variable or toggle to re-enable it in production.
- Files: `app.py` (line 74)
- Impact: Flask-Limiter decorators on `/auth/signin` and `/auth/signup` are silently ignored, leaving the auth endpoints open to brute-force and credential-stuffing attacks.
- Fix approach: Change to `flask_app.config['RATELIMIT_ENABLED'] = os.environ.get('RATELIMIT_ENABLED', 'True').lower() == 'true'` so production can enable rate limiting without a code change.

---

## HIGH

### `google_email` Column Referenced But Not in `init_database()` Schema

- Issue: `routes/google_routes.py` reads and writes a `google_email` column on the `users` table (lines 63, 76, 87, 98). This column is not present in the `CREATE TABLE users` statement in `core/database.py`. A separate `debug/fix_google_column.py` script must be run manually to add it.
- Files: `routes/google_routes.py` (lines 63, 76, 87, 98), `core/database.py` (lines 106-133), `debug/fix_google_column.py`
- Impact: Google OAuth login (create and link) will fail with a database error on any fresh database or after running `init_database()`. This affects demo setup on a new machine.
- Fix approach: Add `google_email TEXT` to the `CREATE TABLE users` block in `core/database.py:init_database()`. Run the migration once for existing databases.

---

### `verify_user()` in `core/database.py` Is a Stub

- Issue: `core/database.py` line 387-389 defines `verify_user()` as: `def verify_user(self, email, password): # ... (Keep existing verify_user) ... pass`. It returns `None` for all calls. The real implementation lives in `core/auth.py:AuthManager.verify_user()`.
- Files: `core/database.py` (lines 387-389)
- Impact: Any code path that calls `db_manager.verify_user()` directly will always return `None`, silently failing authentication. Currently `auth_routes.py` correctly calls `auth_manager.verify_user()`, but the stub is a landmine for future developers.
- Fix approach: Either remove the stub and add a docstring pointing to `AuthManager`, or implement it fully.

---

### CSRF Exemptions on Sensitive Mutation Endpoints

- Issue: Seven POST endpoints that mutate data are decorated with `@csrf.exempt`, including the AI chat endpoint, workflow execution, wallet operations, and admin subscription management.
- Files: `routes/admin_subscription_routes.py` (lines 24, 42), `routes/admin_user_routes.py` (line 85), `routes/ai_routes.py` (lines 112, 155), `routes/wallet_routes.py` (line 103), `routes/workflow_routes.py` (line 90)
- Impact: These endpoints are open to cross-site request forgery. An attacker who can get a logged-in user to visit a malicious page can trigger wallet transfers, subscription changes, and workflow execution.
- Fix approach: Remove `@csrf.exempt` and include a CSRF token in the JavaScript fetch calls using the `csrf_token()` context processor already available in templates.

---

### `OAUTHLIB_INSECURE_TRANSPORT = '1'` Set at Module Level in `app.py`

- Issue: `app.py` line 23 unconditionally sets `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'`, allowing OAuth over plain HTTP. This applies to all environments, including production.
- Files: `app.py` (line 23)
- Impact: OAuth tokens may be transmitted over unencrypted connections in production, exposing Google credentials to network interception.
- Fix approach: Gate this with `if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('OAUTHLIB_INSECURE_TRANSPORT') == '1':`. Remove the unconditional assignment.

---

### `secrets/analytics_service_account.json` and `secrets/token adminmail.json` Require Manual Sharing

- Issue: These two files cannot be committed to git (correctly gitignored via `secrets/`) but are required for Google Analytics and the welcome-email sender to function. There is no documented onboarding path beyond the note in `.env.example`.
- Files: `secrets/analytics_service_account.json`, `secrets/token adminmail.json`, `core/services/analytics_service.py` (line 22), `core/google_integration.py` (line 31)
- Impact: New team members running a fresh clone will see analytics silently fall back to mock data and welcome emails silently fail. The jury demo machine requires these files to be pre-placed manually.
- Fix approach: Document the manual sharing step in `README.md` with exact file paths and who holds them. Consider storing the analytics service account JSON as a base64-encoded environment variable.

---

### Hardcoded Fallback Secret Key in Production Code

- Issue: Both `core/config.py` (line 12) and `app.py` (line 66) supply different hardcoded fallback values for `SECRET_KEY`: `"change_me_random_key"` and `"change_me_to_a_secure_random_value"` respectively. The two fallbacks are inconsistent with each other.
- Files: `core/config.py` (line 12), `app.py` (line 66)
- Impact: If `SECRET_KEY` is not set in the environment, sessions signed with the hardcoded value are universally forgeable. The inconsistency between the two hardcoded values means the Config class's `SECRET_KEY` and the Flask app's `SECRET_KEY` may differ.
- Fix approach: Raise an exception at startup if `SECRET_KEY` is not set in production (check `FLASK_ENV != 'development'`). Remove the second fallback in `app.py` and use `cfg.SECRET_KEY` as the single source of truth.

---

### Google OAuth Token Stored as Plaintext JSON in `users.google_token`

- Issue: The full OAuth token payload (including `access_token`, `refresh_token`, and `client_secret`) is serialized and stored as a plaintext JSON string in the `users` table.
- Files: `routes/google_routes.py` (lines 62, 81, 87), `core/models.py` (line 21)
- Impact: A SQL injection attack or database dump exposes long-lived Google refresh tokens, allowing an attacker to impersonate users across all Google services the app has been granted access to (Drive, Gmail, Sheets, Analytics).
- Fix approach: At minimum, encrypt the token blob using a key derived from `SECRET_KEY` before storing. Better: use a short-lived token cache and re-authenticate with the refresh token server-side.

---

## MEDIUM

### No Dependency Lock File

- Issue: `package/requirements.txt` specifies dependencies with range constraints (`Flask>=3.0,<4.0`) but no lock file (`pip freeze` output, `poetry.lock`, or `uv.lock`) is committed. Several packages (`torch`, `tensorflow`, `transformers`, `Werkzeug`) have no version pin at all.
- Files: `package/requirements.txt`
- Impact: `pip install -r requirements.txt` on a new machine may resolve to different versions than the development environment. Heavy ML packages like `torch` and `tensorflow` have breaking API changes between minor versions.
- Fix approach: Generate and commit a `requirements-lock.txt` via `pip freeze` after a successful installation on the reference machine.

---

### `sqlite3` Imported Directly in Service Layer (Bypasses PGShim)

- Issue: `core/services/product_service.py`, `core/services/customer_service.py`, and `core/services/wallet_service.py` import `sqlite3` directly and catch `sqlite3.IntegrityError`. These catches will silently fail to catch the PostgreSQL equivalent `psycopg2.errors.UniqueViolation` when `USE_POSTGRES=True`.
- Files: `core/services/product_service.py` (line 2, 34), `core/services/customer_service.py` (line 2, 31), `core/services/wallet_service.py` (line 3)
- Impact: Duplicate product/customer code creation errors are not surfaced to the user when running against PostgreSQL. The operation appears to succeed but no record is created.
- Fix approach: Replace `except sqlite3.IntegrityError` with a generic `except Exception as e: if "UNIQUE" in str(e) or "duplicate key" in str(e):` pattern, or import and catch both exception types.

---

### Hardcoded GA Property ID in `analytics_service.py`

- Issue: `core/services/analytics_service.py` line 16 hardcodes `self.property_id = '470037320'` with a comment admitting it is approximate. `core/config.py` defines `GA_PROPERTY_ID = os.environ.get('GA_PROPERTY_ID', '517047582')` — a different value.
- Files: `core/services/analytics_service.py` (line 16), `core/config.py` (line 54)
- Impact: Analytics reports may silently query the wrong GA4 property, returning no data or data from a different account. The discrepancy between the two hardcoded IDs indicates the correct value is unclear.
- Fix approach: Remove the hardcoded fallback in `AnalyticsService.__init__()` and always read from `Config.GA_PROPERTY_ID`.

---

### Bare `except:` Clauses Throughout Core

- Issue: 16 bare `except:` clauses exist across core modules, catching all exceptions including `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit`.
- Files: `core/agent_middleware.py` (lines 4, 29, 33, 45, 55), `core/database.py` (lines 39, 91, 93, 436), `core/make_integration.py` (line 23), `core/workflow_engine.py` (lines 75, 190), `dl_service/utils/ood_detection.py` (line 85)
- Impact: Errors are silently swallowed, making debugging during the jury demo extremely difficult. A crash in a background thread may go unnoticed.
- Fix approach: Replace `except:` with `except Exception:` at minimum. Log the exception with `traceback.format_exc()` before discarding it.

---

### `print()` Used for All Logging in Production Code

- Issue: Over 130 `print()` calls are scattered across `core/` (94) and `routes/` (38), including debug-tagged prints like `print(f'DEBUG: Generated Redirect URI: {redirect_uri}')` in `routes/google_routes.py` line 28.
- Files: `routes/google_routes.py` (lines 28, 37), `routes/auth_routes.py` (line 54), `core/database.py`, `core/auth.py`, `core/google_integration.py`, `dl_service/models/lstm_model.py` (lines 199-215 labeled `[DEBUG]`)
- Impact: Debug output leaks internal URLs, email addresses, and error details to stdout in production. Log aggregation tools cannot filter by level or context. The jury will see raw debug output in the terminal.
- Fix approach: Replace `print()` with `logger = get_logger(__name__)` from `dl_service/utils/logger.py` (already used in `dl_service/`). The main `core/` and `routes/` modules do not yet import from a logger module.

---

### `app.py` Runs `debug=True` in `__main__` Block

- Issue: `app.py` line 226: `app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)`. `run_dl_service.py` line 21 also runs `debug=True`.
- Files: `app.py` (line 226), `run_dl_service.py` (line 21)
- Impact: Flask debug mode enables the interactive debugger (Werkzeug PIN bypass) and auto-reloads, which is a significant security risk if this invocation is used for the demo. The Werkzeug debugger allows arbitrary code execution from the browser.
- Fix approach: Set `debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'` and ensure `FLASK_DEBUG` is not set in the demo environment.

---

### AI Chat Service Depends on External Ngrok/HF URL at Runtime

- Issue: The entire AI chat backend (`routes/ai_routes.py` lines 57, 119) depends on `HF_BASE_URL` pointing to a running ngrok tunnel or HuggingFace Spaces endpoint. This is a third-party URL that can change between sessions.
- Files: `routes/ai_routes.py` (lines 57-69, 119-126), `.env.example` (line 9: `HF_BASE_URL=https://your-ngrok-or-hf-url.ngrok-free.dev`)
- Impact: If the ngrok session expires or the HF Space is sleeping, all AI chat requests fail silently with a connection error. This is a high-probability failure point during a live jury demo.
- Fix approach: Add a `/api/ai/health` preflight check that the frontend calls before the demo. Document the startup sequence (start ngrok/HF Space first, then update `.env`, then start Flask).

---

### No Upload Size Limit in Main Flask App

- Issue: The main Flask app (`app.py`) does not set `MAX_CONTENT_LENGTH`. The `/api/dl/detect`, `/api/ai/upload`, and `/api/workflow/upload_file` endpoints accept files of unlimited size. Only `dl_service/` (separate process) has file validation via `validate_image_file`.
- Files: `app.py`, `routes/dl_routes.py` (line 26), `routes/ai_routes.py` (line 117), `routes/workflow_routes.py` (line 108)
- Impact: An authenticated user can upload arbitrarily large files, causing memory exhaustion on the server. No filename sanitization is applied in `routes/dl_routes.py` or `routes/ai_routes.py` (only `workflow_routes.py` uses `secure_filename`).
- Fix approach: Add `flask_app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024` (16 MB) in `create_app()`. Apply `secure_filename()` in all file upload handlers.

---

## LOW

### `secrets/database.json` Still Referenced by Migration Script

- Issue: `package/migrate_to_postgres.py` still reads connection credentials from `secrets/database.json` as a fallback, even though the project has migrated to `.env` + `python-dotenv`.
- Files: `package/migrate_to_postgres.py` (lines 47-48, 483, 563)
- Impact: A developer running the migration script without understanding the dual-config system may use stale credentials from the JSON file instead of the `.env` file.
- Fix approach: Remove the `secrets/database.json` fallback from `migrate_to_postgres.py` and document that `POSTGRES_URL` must be in `.env`.

---

### `db_manager` Instantiated at Import Time in `core/extensions.py`

- Issue: `core/extensions.py` line 36 creates `db_manager = Database()`, which calls `init_database()` immediately on import (for SQLite). This means the database is initialized before `create_app()` runs and before any configuration can override `DATABASE_PATH`.
- Files: `core/extensions.py` (line 36), `core/database.py` (lines 67-72)
- Impact: Tests that need to override the database path cannot do so after import. A module-level side effect at import time is fragile and can cause issues with multiple Flask app instances (e.g., testing).
- Fix approach: Use lazy initialization — defer `init_database()` to a `Database.init_app(app)` call inside `create_app()`, or move it inside a `with app.app_context():` block.

---

### No Formal Database Migration System

- Issue: Schema changes are applied via ad-hoc `debug/fix_google_column.py` scripts. Although `alembic` is listed in `package/requirements.txt`, there is no `alembic.ini` or `migrations/` directory in the repository.
- Files: `debug/fix_google_column.py`, `debug/migrate_sales_invoice.py`, `package/requirements.txt` (line 92)
- Impact: New team members must discover and run multiple `debug/` scripts manually to get a working database. Missing one causes silent runtime errors. The `google_email` column issue (HIGH concern above) is a direct consequence.
- Fix approach: Initialize alembic (`alembic init migrations`) and convert existing fix scripts into proper migration versions. At minimum, consolidate all `ALTER TABLE` statements into a single `migrate.py` script with clear ordering.

---

### Test Suite Excluded from `.gitignore`

- Issue: `.gitignore` line 7 lists `tests/` as ignored. The test files exist in the working tree but `.gitignore` would exclude them from commits on a freshly cloned repository if ever respected.
- Files: `.gitignore` (line 7)
- Impact: The `tests/` directory is currently tracked (files exist and were committed prior to the ignore entry). The gitignore entry is confusing and inconsistent. New test files added may not be committed by team members unaware of this.
- Fix approach: Remove `tests/` from `.gitignore` since the test suite is intentionally part of the codebase.

---

### Jury Presentation Risks

**High-probability failure points during live demo:**

1. **AI chat will fail** if `HF_BASE_URL` ngrok session has expired between startup and demo time. No fallback or health indicator exists.
2. **Workflow GET/POST/DELETE endpoints will all fail** with `AttributeError` due to the missing `app_module.db` and `app_module.workflow_service` attributes (CRITICAL concern above). This breaks the core workflow builder demo.
3. **Google OAuth login may fail** if `google_email` column is missing from a freshly initialized database.
4. **LSTM forecast will fail** if `dl_service/saved_models/` is empty — no `.h5` or `.pt` files were found in the repository. The model weights must be placed manually before demo.
5. **Deep learning service startup is slow** — PyTorch, TensorFlow, PaddleOCR, and EasyOCR all load heavy models at startup. Allocate 2-5 minutes for the DL service to be ready before the demo.
6. **Two separate processes required** — `app.py` (port 5000) and the DL service (port 5001) must both be running. There is no unified startup script.

---

*Concerns audit: 2026-05-16*
