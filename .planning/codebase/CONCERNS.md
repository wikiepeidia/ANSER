# Codebase Concerns

**Analysis Date:** 2026-06-08

## Tech Debt

**Database schema split across multiple sources:**
- Issue: Schema definitions live in `core/db/connection.py`, `migrations/versions/001_initial_schema.py`, `migrations/001_add_password_version.py`, and `package/migrate_to_postgres.py`, with route and service code referencing columns/tables that are not present in all definitions.
- Files: `core/db/connection.py`, `migrations/versions/001_initial_schema.py`, `migrations/001_add_password_version.py`, `package/migrate_to_postgres.py`, `routes/google_routes.py`, `core/automation_engine.py`
- Impact: New database setup paths diverge. Features such as Google login, password migration, and automation procurement can fail depending on which schema path initialized the database.
- Fix approach: Treat Alembic migrations under `migrations/versions/` as the canonical schema, add missing migrations for referenced fields/tables, and remove ad hoc DDL from package/setup scripts or generate it from the canonical migrations.

**Database facade mixes connection, migration, schema, and repository concerns:**
- Issue: `core/db/connection.py` owns SQLite creation, PostgreSQL pooling, cursor shimming, placeholder rewriting, facade methods, and table initialization in one module.
- Files: `core/db/connection.py`
- Impact: The PostgreSQL shim rewrites SQL placeholders and appends `RETURNING id` to inserts, making behavior sensitive to query text and primary-key assumptions. Connection lifecycle and schema setup are hard to change without affecting service behavior.
- Fix approach: Split connection management, schema/migration setup, and repository facades into separate modules. Use a real PostgreSQL query path instead of regex placeholder conversion inside `PGShimCursor`.

**App factory is coupled to module-level globals:**
- Issue: `app.py` creates `config`, `app`, `current_user`, `db_manager`, and services at module scope, while route modules import the live `app` module through helper functions.
- Files: `app.py`, `core/extensions.py`, `routes/workflow_routes.py`, `routes/inventory_routes.py`, `routes/ai_routes.py`
- Impact: Import order determines runtime state. Tests rely on monkeypatching module globals, and production setup can initialize the database before app configuration is fully applied.
- Fix approach: Keep application state in Flask extensions, `g`, or dependency-injected service factories. Route modules should use `current_app` and request-scoped dependencies rather than importing `app` module globals.

**Large frontend modules concentrate workflow complexity:**
- Issue: `static/js/workspace_builder.js` is a large stateful builder script that handles graph state, DOM rendering, execution previews, file uploads, logging, and mock fallbacks in one file.
- Files: `static/js/workspace_builder.js`, `static/js/admin_products.js`, `static/js/admin_subscriptions.js`, `static/js/scenarios.js`
- Impact: Behavior changes are difficult to isolate, and this surface is omitted from coverage. Mock/demo data can hide backend failures during manual testing.
- Fix approach: Split builder state, rendering, API calls, and mock/demo behavior into focused modules. Add browser-level or DOM-level tests for workflow building and admin UI flows.

**Mock and fallback behavior is reachable from production code paths:**
- Issue: Several integrations fall back to mock responses or silently initialized local models when credentials, data, or model files are missing.
- Files: `core/google_integration.py`, `static/js/admin_products.js`, `static/js/admin_subscriptions.js`, `dl_service/services/model_loader.py`, `dl_service/services/forecast_service.py`, `dl_service/api/history_routes.py`
- Impact: Failed integrations can appear successful with mock data, untrained models, or placeholder responses. This creates false confidence in demos and masks production misconfiguration.
- Fix approach: Gate mocks behind an explicit development/demo flag, return clear integration errors by default, and expose model readiness status separately from successful prediction status.

## Known Bugs

**Password reset stores a hash format that login does not verify:**
- Symptoms: A user whose password is reset through `core/services/user_service.py` can receive a Werkzeug password hash while `core/auth.py` verifies versioned bcrypt hashes.
- Files: `core/auth.py`, `core/services/user_service.py`
- Trigger: Call `UserService.reset_password()` for a user whose `password_version` is `1`, then attempt password login through the bcrypt verifier.
- Workaround: Not detected.

**Google OAuth references schema fields that are missing from canonical schema definitions:**
- Symptoms: Google login and account linking query or update `google_email`, but the initial SQLite/Alembic/package schemas do not define that column.
- Files: `routes/google_routes.py`, `core/db/connection.py`, `migrations/versions/001_initial_schema.py`, `package/migrate_to_postgres.py`
- Trigger: Use `/auth/google` or `/auth/google/callback` against a database initialized from the current initial schema.
- Workaround: Manually alter the users table to add the expected Google account fields.

**Google-created accounts use a different password hashing scheme:**
- Symptoms: New users created by Google login receive a Werkzeug password hash while the login path expects versioned bcrypt hashes.
- Files: `routes/google_routes.py`, `core/auth.py`
- Trigger: Create a user through the Google callback path, then later attempt password authentication for that account.
- Workaround: Force a reset path that writes a compatible bcrypt hash once `UserService.reset_password()` is corrected.

**Automation procurement references missing tables and columns:**
- Symptoms: Low-stock automation queries `products.import_price`, reads from `suppliers`, and inserts `supplier_id` into `import_transactions`, but the current schemas do not define those fields/tables.
- Files: `core/automation_engine.py`, `core/db/connection.py`, `migrations/versions/001_initial_schema.py`
- Trigger: Execute automation rules that call low-stock procurement or scheduled import logic.
- Workaround: Not detected.

**Sales deletion is not scoped to the current user:**
- Symptoms: Sales history reads are user-scoped, but deletion uses only `sale_id`.
- Files: `core/services/sales_service.py`, `routes/sales_routes.py`
- Trigger: Submit a delete request for a sale ID belonging to another user while authenticated.
- Workaround: Restrict access at the database or service layer before exposing sales IDs across users.

**Product and customer records are globally readable and mutable despite creator fields:**
- Symptoms: Product and customer creation records `created_by`, but list/update/delete/import functions do not filter by owner or role.
- Files: `routes/main_routes.py`, `core/services/product_service.py`, `core/services/customer_service.py`
- Trigger: Any authenticated user loads products/customers or calls update/delete APIs using IDs from shared records.
- Workaround: Not detected.

**PostgreSQL package migration schema differs from runtime services:**
- Symptoms: The package migration DDL omits runtime fields such as `password_version` and Google account fields, and transaction table shapes differ from the Alembic/core schema.
- Files: `package/migrate_to_postgres.py`, `core/auth.py`, `routes/google_routes.py`, `migrations/versions/001_initial_schema.py`
- Trigger: Initialize PostgreSQL through `package/migrate_to_postgres.py` and run authentication or Google account flows.
- Workaround: Initialize through canonical Alembic migrations rather than the package migration script.

## Security Considerations

**Local ignored AI demo contains hardcoded credentials:**
- Risk: `ai_agent_service/launch_demo.py` contains a hardcoded PostgreSQL connection URL and ngrok auth token. Values are intentionally omitted from this document.
- Files: `ai_agent_service/launch_demo.py`, `.gitignore`
- Current mitigation: `ai_agent_service/launch_demo.py` is ignored by `.gitignore`, so it is not tracked in the current repository index.
- Recommendations: Rotate the exposed credentials, delete hardcoded secrets from the workspace, and load these values only from environment variables or a secret manager.

**Secret-bearing files and archives exist in the workspace:**
- Risk: Root environment and secret artifacts can be accidentally staged or copied into planning/output artifacts.
- Files: `.env`, `secrets/`, `secrets.rar`, `.env.example`, `.gitignore`
- Current mitigation: `.env`, `secrets/`, and `*.rar` are ignored by `.gitignore`.
- Recommendations: Keep `.env.example` placeholder-only, add secret scanning to CI, and avoid reading or quoting secret files in tools and documentation.

**Production hardening settings are disabled in the Flask app:**
- Risk: Session cookies, HTTPS enforcement, HSTS, CSP, and rate limiting are configured in a permissive state.
- Files: `app.py`
- Current mitigation: `app.py` requires a non-default `SECRET_KEY` outside development.
- Recommendations: Enable `SESSION_COOKIE_SECURE`, HTTPS enforcement, HSTS, rate limiting, and a stricter CSP for deployed environments. Keep permissive settings limited to local development config.

**CSRF protection is bypassed on authenticated JSON mutation routes:**
- Risk: Browser-authenticated users can be targeted by cross-site requests on routes exempted from CSRF.
- Files: `routes/admin_subscription_routes.py`, `routes/main_routes.py`, `routes/wallet_routes.py`, `routes/workflow_routes.py`
- Current mitigation: Routes still perform login/admin checks where decorators are present.
- Recommendations: Require CSRF tokens for state-changing browser routes, or use a separate API auth mechanism that is not automatically attached by browsers.

**AI agent service exposes unauthenticated endpoints with permissive CORS:**
- Risk: The FastAPI service accepts chat, upload, and OCR requests without app-level authentication, while CORS allows all origins with credentials enabled.
- Files: `ai_agent_service/src/server.py`
- Current mitigation: Not detected.
- Recommendations: Add authentication, constrain allowed origins, enforce upload size/type limits, and separate internal service access from public routes.

**Workflow integrations can exfiltrate data through user-configured webhooks:**
- Risk: Workflow steps can resolve prior-step data and send payloads to arbitrary URLs.
- Files: `core/workflow_engine.py`, `core/make_integration.py`, `routes/workflow_routes.py`
- Current mitigation: Workflow routes require login.
- Recommendations: Validate destination domains, block private-network SSRF targets, redact payload logs, and record explicit user ownership for every integration target.

**Exceptions and payload logs can expose sensitive data:**
- Risk: API routes return `str(error)` to clients, and logs include payloads, OCR text, user messages, resolved workflow data, and external request URLs.
- Files: `app.py`, `routes/dl_routes.py`, `routes/ai_routes.py`, `routes/workflow_routes.py`, `routes/admin_subscription_routes.py`, `routes/wallet_routes.py`, `routes/main_routes.py`, `core/make_integration.py`, `core/workflow_engine.py`, `dl_service/services/invoice_service.py`, `ai_agent_service/src/server.py`
- Current mitigation: `core/logger.py` creates rotating log files.
- Recommendations: Return stable error codes/messages to clients, log structured redacted context, and keep sensitive payloads out of persistent logs.

**Calculator tool evaluates user-provided expressions:**
- Risk: The AI agent calculator uses `eval()` on user-controlled expressions, with builtins removed but no expression parser.
- Files: `ai_agent_service/src/core/tools.py`
- Current mitigation: `__builtins__` is set to `None`.
- Recommendations: Replace `eval()` with a small AST-based arithmetic parser or a safe expression library.

## Performance Bottlenecks

**AI chat route starts an unbounded background thread per request:**
- Problem: Long-running AI calls are dispatched with raw `threading.Thread`, write job files to disk, and instantiate database/agent services inside each thread.
- Files: `routes/ai_routes.py`, `jobs/`
- Cause: There is no queue, worker pool, cancellation, concurrency limit, or cleanup policy.
- Improvement path: Move background AI work to a bounded job queue with retry, timeout, cancellation, and retention controls.

**Model services load heavy models at import or startup:**
- Problem: FastAPI and DL services initialize model engines during module load/startup, including large language, vision, YOLO, and LSTM components.
- Files: `ai_agent_service/src/server.py`, `ai_agent_service/src/core/config.py`, `ai_agent_service/src/core/engine.py`, `dl_service/model_app.py`, `dl_service/services/model_loader.py`
- Cause: Global service instances and startup initialization eagerly load model weights.
- Improvement path: Use lazy loading with health/readiness endpoints, warmup hooks, and per-model resource limits.

**Forecasting reloads CSV data on request paths:**
- Problem: Forecast service reads historical CSV files for forecast generation instead of caching parsed data or storing it in the application database.
- Files: `dl_service/services/forecast_service.py`
- Cause: `load_timescale_data()` reads local CSV files each time data is needed.
- Improvement path: Cache immutable datasets, use database-backed time series, and invalidate cache explicitly when source data changes.

**File upload routes read whole files into memory or accept broad uploads:**
- Problem: Excel import preview, workflow upload, AI upload, and DL detection paths accept uploaded files without consistent size/type enforcement at the Flask proxy layer.
- Files: `routes/main_routes.py`, `routes/workflow_routes.py`, `routes/ai_routes.py`, `routes/dl_routes.py`, `core/services/product_service.py`
- Cause: The routes read request files directly and rely on downstream behavior or extension checks.
- Improvement path: Enforce `MAX_CONTENT_LENGTH`, validate MIME/type and size at the route boundary, stream large files, and reject unsupported uploads before downstream processing.

**Large static JavaScript increases parse and maintenance cost:**
- Problem: The workspace builder is a multi-thousand-line static script loaded as a single behavioral unit.
- Files: `static/js/workspace_builder.js`
- Cause: UI state management, rendering, API integration, mock fallbacks, and workflow execution handling are bundled together.
- Improvement path: Split modules, defer non-critical code, and add a build/test step for frontend behavior.

## Fragile Areas

**SQL placeholder conversion and implicit insert IDs:**
- Files: `core/db/connection.py`
- Why fragile: The PostgreSQL shim uses text rewriting for `?` placeholders and mutates insert SQL to add `RETURNING id`, then falls back on failure.
- Safe modification: Add regression tests for every query shape before changing database code, and move service queries to explicit PostgreSQL-compatible SQL or a query builder.
- Test coverage: Current tests cover selected services, but they do not exercise every SQLite/PostgreSQL query conversion path.

**Authentication schema fallback masks missing migrations:**
- Files: `core/auth.py`, `migrations/001_add_password_version.py`, `migrations/versions/001_initial_schema.py`
- Why fragile: Login catches `OperationalError` around `password_version` and falls back to legacy verification, which can hide a missing migration in local testing.
- Safe modification: Require migration status checks at startup and fail fast when auth schema fields are absent.
- Test coverage: Existing auth tests cover integration paths, but reset/Google hash format mismatches are not covered.

**Workflow execution returns logs and resolved data through API responses:**
- Files: `core/workflow_engine.py`, `routes/workflow_routes.py`, `core/make_integration.py`
- Why fragile: Workflow logs include resolved payloads and external call details, then route responses expose execution results to callers.
- Safe modification: Redact logs before persistence/response and separate user-visible execution status from internal debug traces.
- Test coverage: Workflow service tests cover CRUD/delegation patterns, but they do not validate log redaction or SSRF prevention.

**DL client mutates import paths for local service fallback:**
- Files: `core/services/dl_client.py`, `dl_service/services/invoice_service.py`, `dl_service/services/forecast_service.py`
- Why fragile: Local processing appends `dl_service/` to `sys.path` and imports modules by generic `services.*` names, which can collide with other packages or import stale modules.
- Safe modification: Package `dl_service` as an importable module and use fully qualified imports.
- Test coverage: DL service code is omitted from coverage by `.coveragerc`.

**Frontend mocks can obscure backend contract failures:**
- Files: `static/js/admin_products.js`, `static/js/admin_subscriptions.js`, `static/js/workspace_builder.js`, `static/js/scenarios.js`
- Why fragile: UI scripts render fallback/mock data after failed API calls, making broken backend contracts look like populated screens.
- Safe modification: Confine mock behavior to explicit demo mode and show error states in normal runtime.
- Test coverage: Static frontend files are omitted from coverage by `.coveragerc` and have no detected browser tests.

## Scaling Limits

**Small PostgreSQL pool with unbounded concurrent background work:**
- Current capacity: PostgreSQL pool is configured with `maxconn=10`.
- Limit: Raw AI background threads and web requests can exhaust database connections without queue backpressure.
- Scaling path: Add a bounded worker queue, connection acquisition timeouts, and per-route concurrency limits.

**Runtime artifacts accumulate on local disk:**
- Current capacity: Jobs, uploads, and logs are stored under local directories.
- Limit: `jobs/`, `uploads/`, and `logs/` can grow without retention limits and are unsuitable for horizontally scaled deployments.
- Scaling path: Add retention cleanup, move user files to managed object storage, and store job metadata in a database-backed queue.

**In-memory state is not process-safe:**
- Current capacity: Import previews, invoice history, accuracy stats, model readiness, and loaded models are kept in module-level memory.
- Limit: Multiple workers or restarts lose state and can disagree about readiness or pending import files.
- Scaling path: Store pending import metadata, model status, and job state in a shared database/cache and make model instances worker-local with explicit readiness.

**SQLite fallback limits multi-user production behavior:**
- Current capacity: The app can initialize and run on a local SQLite database.
- Limit: SQLite locking and local file storage do not scale with concurrent users, background jobs, or multi-process deployments.
- Scaling path: Require PostgreSQL for deployed environments and reserve SQLite for isolated tests/development.

## Dependencies at Risk

**AI/DL dependency stack is operationally heavy and partially outside coverage:**
- Risk: Model-serving code depends on large ML runtimes and local model artifacts while being excluded from coverage.
- Impact: Dependency, GPU, and model-path changes can break startup or inference without CI detection.
- Migration plan: Pin model/runtime versions, add smoke tests for model readiness, and isolate optional AI/DL services behind explicit health checks.

**Ignored AI agent service is referenced as runtime infrastructure:**
- Risk: `ai_agent_service/` is ignored by `.gitignore`, but route code and local scripts treat it as an application service.
- Impact: Developers or deployment environments can miss service code, model adapters, or launch scripts that are required for AI functionality.
- Migration plan: Either commit a sanitized service package with tests and docs, or mark it as an external service with a stable API contract and deployment instructions.

**Remote-code model loading increases supply-chain risk:**
- Risk: The AI engine enables remote model code execution for model loading.
- Impact: Model source changes can execute code in the service process.
- Migration plan: Pin trusted model revisions, avoid remote code when possible, and run model services in a restricted environment.

**Google integration mock fallback weakens dependency failure visibility:**
- Risk: Missing credentials or API failures can return mock data rather than a clear integration failure.
- Impact: Google Sheets/Docs/Gmail issues can remain hidden until real business operations depend on them.
- Migration plan: Make external API dependencies fail closed outside demo mode and add contract tests with mocked Google clients.

## Missing Critical Features

**Consistent tenant and ownership authorization:**
- Problem: Products, customers, inventory reports, scheduled reports, automations, and selected delete operations are not consistently scoped by `current_user`.
- Blocks: Safe multi-user operation where users should not read, modify, or delete each other's business data.

**Production configuration profile:**
- Problem: Security-sensitive Flask settings are hardcoded permissively in the app factory instead of derived from a production profile.
- Blocks: Safe deployment without manually auditing every runtime setting.

**Secret scanning and rotation workflow:**
- Problem: The workspace contains ignored secret artifacts and a local file with hardcoded credentials.
- Blocks: Confident commits, deployments, and onboarding without accidental secret exposure.

**Central upload validation and retention policy:**
- Problem: Upload validation is spread across routes and downstream services, and local upload/job files do not have a visible retention lifecycle.
- Blocks: Safe handling of large, malicious, or stale user files.

**Operational job queue for AI and automation:**
- Problem: Long-running AI work and workflow automation run through request threads or raw background threads.
- Blocks: Reliable retries, concurrency limits, cancellation, observability, and horizontal scaling.

**Model readiness and training status contract:**
- Problem: DL model loading can fall back to fresh/untrained models, and a training endpoint is marked unimplemented.
- Blocks: Trustworthy forecasting/inference results and operator visibility into model quality.

## Test Coverage Gaps

**Authentication edge cases:**
- What's not tested: Password reset hash compatibility, Google OAuth schema requirements, and Google-created account password compatibility.
- Files: `core/auth.py`, `core/services/user_service.py`, `routes/google_routes.py`, `tests/`
- Risk: Users can be locked out after reset or OAuth account creation.
- Priority: High

**Ownership and authorization boundaries:**
- What's not tested: Cross-user product/customer access, sales deletion by non-owner, global dashboard/report visibility, and scheduled report/automation ownership.
- Files: `core/services/product_service.py`, `core/services/customer_service.py`, `core/services/sales_service.py`, `core/services/operations_service.py`, `routes/main_routes.py`, `routes/sales_routes.py`, `tests/`
- Risk: Authenticated users can access or mutate data outside their account boundary.
- Priority: High

**CSRF, rate limiting, and deployed security settings:**
- What's not tested: CSRF enforcement and rate limiting behavior because test config disables both.
- Files: `tests/conftest.py`, `app.py`, `routes/admin_subscription_routes.py`, `routes/main_routes.py`, `routes/wallet_routes.py`, `routes/workflow_routes.py`
- Risk: Security regressions pass tests while browser-exposed mutation routes remain vulnerable.
- Priority: High

**Schema parity across initialization paths:**
- What's not tested: Equivalence between SQLite schema creation, Alembic migrations, and package PostgreSQL migration scripts.
- Files: `core/db/connection.py`, `migrations/versions/001_initial_schema.py`, `migrations/001_add_password_version.py`, `package/migrate_to_postgres.py`, `tests/`
- Risk: New databases miss columns/tables used by runtime code.
- Priority: High

**AI, DL, frontend, and static UI surfaces are omitted from coverage:**
- What's not tested: AI agent API, DL model services, static JavaScript workflows, and UI behavior.
- Files: `.coveragerc`, `ai_agent_service/src/server.py`, `dl_service/`, `static/js/workspace_builder.js`, `static/js/admin_products.js`, `static/js/admin_subscriptions.js`
- Risk: Large user-facing and model-facing surfaces can break without CI feedback.
- Priority: Medium

**Workflow integration security behavior:**
- What's not tested: SSRF blocking, webhook destination validation, log redaction, upload validation, and workflow execution data exposure.
- Files: `core/workflow_engine.py`, `core/make_integration.py`, `routes/workflow_routes.py`, `tests/services/test_workflow_service.py`
- Risk: Workflow automation can leak sensitive data or call unsafe destinations unnoticed.
- Priority: High

**Upload size/type enforcement:**
- What's not tested: Oversized, malformed, and unsupported uploads for Excel import, workflow uploads, AI uploads, and DL detection.
- Files: `routes/main_routes.py`, `routes/workflow_routes.py`, `routes/ai_routes.py`, `routes/dl_routes.py`, `tests/services/test_product_import.py`
- Risk: Memory pressure, disk growth, and unsupported file handling can fail in production request paths.
- Priority: Medium

---

*Concerns audit: 2026-06-08*
