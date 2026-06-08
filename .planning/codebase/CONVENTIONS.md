# Coding Conventions

**Analysis Date:** 2026-06-08

## Naming Patterns

**Files:**
- Use snake_case Python module names for backend code, as in `core/services/inventory_tx_service.py`, `core/services/product_service.py`, `core/db/user_repo.py`, and `routes/admin_user_routes.py`.
- Use `*_routes.py` for Flask blueprint modules, as in `routes/inventory_routes.py`, `routes/workflow_routes.py`, and `routes/admin_subscription_routes.py`.
- Use `*_service.py` for service-layer modules, as in `core/services/workflow_service.py`, `core/services/ai_chat_service.py`, and `core/services/wallet_service.py`.
- Use `*_repo.py` for repository modules that wrap database tables, as in `core/db/user_repo.py`, `core/db/workflow_repo.py`, `core/db/activity_repo.py`, and `core/db/chat_repo.py`.
- Use page-specific JavaScript filenames under `static/js/` matching templates under `ui/templates/`, as in `static/js/admin_products.js` with `ui/templates/products.html` and `static/js/admin_dashboard.js` with `ui/templates/admin_dashboard.html`.
- Use page-specific CSS filenames under `static/css/` matching templates under `ui/templates/`, as in `static/css/admin_products.css` with `ui/templates/products.html`.
- Use pytest discovery names `test_*.py` under `tests/`, as configured by `pytest.ini` and used by `tests/services/test_inventory_tx_service.py`, `tests/contracts/test_contract_routes.py`, and `tests/parity/test_endpoint_middleware_parity.py`.

**Functions:**
- Use snake_case for Python functions and private helpers, as in `create_app()` and `_configure_oauth()` in `app.py`, `create_import_transaction()` and `_require_payload()` in `core/services/inventory_tx_service.py`, and `_route_method_map()` in `tests/contracts/test_contract_routes.py`.
- Prefix private module helpers with `_`, as in `_decode_google_token()` in `core/services/workflow_service.py`, `_app_module()` in `routes/workflow_routes.py`, and `_make_mem_conn()` in `tests/services/conftest.py`.
- Use route handler names that describe the endpoint action, as in `api_create_import()` in `routes/inventory_routes.py`, `admin_promote_user()` in `routes/admin_user_routes.py`, and `run_workflow()` in `routes/workflow_routes.py`.
- Use camelCase for frontend JavaScript functions and DOM helpers, as in `loadProducts()`, `renderProductsTable()`, and `openAddProductModal()` in `static/js/admin_products.js`.
- Use `test_...` names for pytest test functions, as in `test_create_export_transaction_rolls_back_on_insufficient_stock()` in `tests/services/test_inventory_tx_service.py`.

**Variables:**
- Use snake_case for Python locals, parameters, and payload fields, as in `user_id`, `workflow_data`, and `google_token_raw` in `core/services/workflow_service.py`.
- Use lower-case blueprint names ending in `_bp`, as in `inventory_bp` in `routes/inventory_routes.py`, `workflow_bp` in `routes/workflow_routes.py`, and `admin_user_bp` in `routes/admin_user_routes.py`.
- Use UPPER_CASE for module constants, with a leading underscore for private constants, as in `_LOGS_DIR`, `_LOG_FILE`, `_MAX_BYTES`, and `_BACKUP_COUNT` in `core/logger.py`; `FIELD_LABELS` and `_FIELD_KEYWORDS` in `core/services/product_service.py`; and `MANIFEST_PATH` in `tests/contracts/test_contract_routes.py`.
- Use snake_case keys for API request and response payloads, as in `supplier_name`, `stock_quantity`, and `product_id` in `core/services/inventory_tx_service.py` and `static/js/admin_imports.js`.
- Use camelCase for JavaScript variables that represent DOM state or functions, as in `productsData`, `editingId`, and `alertDiv` in `static/js/admin_products.js`.
- Use local stub variables named for their role in tests, as in `conn`, `called`, `automation_stub`, and `payload_json` in `tests/services/test_inventory_route_delegation.py`.

**Types:**
- Use PascalCase for Python classes, as in `Config` in `core/config.py`, `Database` and `PGShimConnection` in `core/database.py`, `User` in `core/models.py`, and `AuthManager` in `core/auth.py`.
- Use PascalCase with leading underscores for private test/support classes, as in `_ConnStub`, `_DbManagerStub`, and `_AutomationStub` in `tests/services/test_inventory_route_delegation.py`.
- Use dataclasses and type annotations in ML/service modules that already use them, as in `LayoutRegion` and `detect_layout_regions(image: np.ndarray, conf_threshold: float = 0.70)` in `dl_service/services/layout_service.py`.
- Keep core Flask service modules mostly annotation-light unless the local file already uses annotations, as in `core/services/workflow_service.py`, `core/services/inventory_tx_service.py`, and `core/services/product_service.py`.

## Code Style

**Formatting:**
- No repo-level formatter config is detected: `pyproject.toml`, `ruff.toml`, `.prettierrc`, `biome.json`, and `eslint.config.*` are not present at the project root.
- Use 4-space indentation for Python code, matching `app.py`, `core/services/inventory_tx_service.py`, and `tests/services/test_inventory_tx_service.py`.
- Use 4-space indentation for plain JavaScript files, matching `static/js/admin_products.js`, `static/js/admin_imports.js`, and `static/js/wallet.js`.
- Preserve the quote style of the file being edited: many route/config files use single quotes in `routes/admin_user_routes.py` and `core/config.py`, while newer extracted services/tests commonly use double quotes in `core/services/workflow_service.py` and `tests/services/test_inventory_tx_service.py`.
- Keep SQL statements parameterized with `?` placeholders in application code, as in `core/services/inventory_tx_service.py`, `core/services/workflow_service.py`, and `core/db/user_repo.py`; the PostgreSQL shim in `core/database.py` converts placeholders for PostgreSQL connections.
- Use multi-line SQL strings for long statements and align parameter tuples directly below the statement, as in `core/services/inventory_tx_service.py`, `core/services/product_service.py`, and `tests/integration/test_catalog_crud_smoke.py`.
- Keep HTML/Jinja page templates under `ui/templates/` using `{% extends "base.html" %}`, `{% block styles %}`, `{% block scripts %}`, and `{% block content %}`, as in `ui/templates/admin_dashboard.html`, `ui/templates/admin_managers.html`, and `ui/templates/admin_roles.html`.

**Linting:**
- No linting config is detected: `.eslintrc*`, `eslint.config.*`, `ruff.toml`, `pyproject.toml`, `setup.cfg`, `tox.ini`, and `biome.json` are not present at the project root.
- Do not introduce a new linting style in one file only; match the local style in files such as `routes/inventory_routes.py`, `core/services/product_service.py`, and `static/js/admin_products.js`.
- `requirements-dev.txt` includes pytest tooling only; it does not define `ruff`, `black`, `flake8`, `mypy`, ESLint, or Prettier.

## Import Organization

**Order:**
1. Standard library imports first, as in `app.py` (`os`, `sys`, `threading`, `datetime`) and `tests/test_workflow_crud.py` (`sqlite3`, `json`).
2. Third-party imports next, as in `app.py` (`flask`, `werkzeug`, `flask_wtf`, `flask_talisman`, `authlib`) and `tests/services/test_inventory_tx_service.py` (`pytest`).
3. Local application imports last, as in `app.py` (`core.extensions`, `core.models`, `core.auth`, `core.config`) and `routes/inventory_routes.py` (`core.services`, `core.excel_parser`, `core.logger`).
4. Use a blank line between import groups, matching `tests/services/test_inventory_tx_service.py`, `tests/test_auth_integration.py`, and `core/services/workflow_service.py`.
5. Keep lazy imports only for circular dependency avoidance or optional runtime dependencies, as in `_app_module()` in `routes/workflow_routes.py`, `_app_module()` in `routes/inventory_routes.py`, and `PGShimConnection.cursor()` in `core/database.py`.

**Path Aliases:**
- Use repository-root Python imports through `pythonpath = .` in `pytest.ini`, as in `from core.auth import AuthManager` in `tests/test_auth_integration.py` and `import core.services.inventory_tx_service as inventory_tx_service` in `tests/services/test_inventory_tx_service.py`.
- Use absolute local package imports for backend code, as in `from core.extensions import csrf` in `routes/workflow_routes.py` and `from core.logger import get_logger` in `routes/inventory_routes.py`.
- Use relative imports inside the service package only when the file already does so, as in `from .service_errors import ServiceValidationError` in `core/services/workflow_service.py`.
- No JavaScript module bundler aliases are detected; frontend files under `static/js/` use browser globals and page script tags in `ui/templates/*.html`.

## Error Handling

**Patterns:**
- Route handlers return JSON dictionaries with `success`, `message`, `error`, or data keys through `jsonify`, as in `routes/inventory_routes.py`, `routes/admin_user_routes.py`, and `routes/workflow_routes.py`.
- Route handlers map validation and authorization errors to HTTP status codes near the route, as in `routes/inventory_routes.py` catching `ServiceValidationError` as 400 and `ServiceInvariantError` as 500.
- Use service-layer exception classes from `core/services/service_errors.py` for route-to-service boundaries: `ServiceValidationError`, `ServiceAuthorizationError`, and `ServiceInvariantError`.
- Use built-in `LookupError`, `PermissionError`, and `ValueError` for simple domain failures in modules that already use them, as in `core/services/user_service.py`, `core/services/workspace_service.py`, and `core/services/wallet_service.py`.
- Wrap database writes in `try` blocks with `commit()` on success and `rollback()` on failure, as in `core/services/inventory_tx_service.py`, `core/services/product_service.py`, and `core/services/user_service.py`.
- Close database connections in `finally` blocks or context managers, as in `routes/workflow_routes.py`, `routes/inventory_routes.py`, `core/services/user_service.py`, and `core/database.py`.
- Keep Flask request globals out of service modules. `tests/services/test_extraction_contracts.py` asserts that `core/services/workflow_service.py`, `core/services/ai_chat_service.py`, and `core/services/inventory_tx_service.py` do not import Flask globals.
- Use `request.get_json(silent=True) or {}` in JSON routes that accept optional payloads, as in `routes/inventory_routes.py` and `routes/workflow_routes.py`.
- Use application-level Flask error handlers for cross-cutting CSRF/API errors in `app.py`; route-specific errors still belong in route modules such as `routes/inventory_routes.py`.

## Logging

**Framework:** `logging` through `core/logger.py`

**Patterns:**
- Use `logger = get_logger(__name__)` for backend modules that log application events, as in `routes/inventory_routes.py`, `core/auth.py`, `core/automation_engine.py`, and `core/db/user_repo.py`.
- Use `logger.info`, `logger.warning`, and `logger.error(..., exc_info=True)` for operational events and exceptions, as in `core/auth.py`, `routes/inventory_routes.py`, and `core/automation_engine.py`.
- `core/logger.py` configures JSON-formatted logs to `logs/app.log` and stdout through shared handlers; reuse `get_logger()` rather than creating ad hoc handlers.
- Use `print()` only in process bootstrap, demo, or ML/model initialization scripts that already use console output, as in `app.py`, `run_dl_service.py`, `dl_service/services/model_loader.py`, and `dl_service/services/invoice_service.py`.
- Do not log secret values. Configuration code reads environment variable names in `core/config.py` and `app.py`; logs should reference missing configuration by name only.

## Comments

**When to Comment:**
- Use module docstrings to state ownership and purpose, as in `core/services/inventory_tx_service.py`, `routes/workflow_routes.py`, `core/extensions.py`, and `tests/services/conftest.py`.
- Use docstrings for service functions that define transaction or boundary behavior, as in `create_import_transaction()` in `core/services/inventory_tx_service.py`, `execute_user_workflow()` in `core/services/workflow_service.py`, and `import_products_from_excel()` in `core/services/product_service.py`.
- Use short comments for non-obvious compatibility constraints, schema fallbacks, and circular import avoidance, as in `app.py`, `core/database.py`, `core/extensions.py`, and `routes/inventory_routes.py`.
- Keep comments close to the code they explain. Avoid adding large narrative comments in route handlers such as `routes/admin_user_routes.py` or page scripts such as `static/js/admin_products.js`.

**JSDoc/TSDoc:**
- JSDoc is not used in `static/js/admin_products.js`, `static/js/admin_imports.js`, or `static/js/workspace_builder.js`.
- Prefer small function names and local comments over adding JSDoc blocks to plain browser scripts under `static/js/` unless a file already establishes that pattern.

## Function Design

**Size:** Keep new backend functions focused around one endpoint, service operation, or repository query; extracted service functions in `core/services/workflow_service.py`, `core/services/ai_chat_service.py`, and `core/services/inventory_tx_service.py` are the preferred shape for new business logic.

**Parameters:** Pass dependencies explicitly into service functions when practical, as in `create_import_transaction(db_conn, user_id, payload)` in `core/services/inventory_tx_service.py` and `execute_user_workflow(workflow_data, google_token_raw)` in `core/services/workflow_service.py`.

**Return Values:** Return plain dictionaries, lists, booleans, or `None` from service/repository code, as in `core/services/workflow_service.py`, `core/services/inventory_tx_service.py`, `core/services/product_service.py`, and `core/db/user_repo.py`.

**Route Functions:**
```python
# Pattern from `routes/inventory_routes.py`
data = request.get_json(silent=True) or {}
conn = app_module.db_manager.get_connection()
try:
    result = inventory_tx_service.create_import_transaction(conn, app_module.current_user.id, data)
    return jsonify({"success": True, "id": result["id"]})
except ServiceValidationError as e:
    return jsonify({"success": False, "message": str(e)}), 400
finally:
    conn.close()
```

**Service Functions:**
```python
# Pattern from `core/services/workflow_service.py`
def list_workflows_for_user(db_conn, user_id):
    if user_id is None:
        raise ServiceValidationError("user_id is required")

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT id, name, data, created_at, updated_at FROM workflows "
        "WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    )
    return [...]
```

**Frontend Functions:**
```javascript
// Pattern from `static/js/admin_products.js`
async function loadProducts() {
    try {
        const response = await fetch('/api/products');
        const data = await response.json();
        if (data.success) {
            productsData = data.products;
            renderProductsTable();
        }
    } catch (error) {
        showAlert('error', 'Error: ' + error.message);
    }
}
```

## Module Design

**Exports:** Python modules export functions, classes, and blueprint variables directly; there is no explicit `__all__` pattern in `app.py`, `routes/inventory_routes.py`, `core/services/workflow_service.py`, or `core/db/user_repo.py`.

**Barrel Files:** `routes/__init__.py` is a package marker only. No `core/services/__init__.py` file is detected, so import concrete service modules or functions directly from files such as `core/services/user_service.py`, `core/services/product_service.py`, and `core/services/inventory_tx_service.py`.

**Blueprint Modules:**
- Define one `Blueprint` per route module, as in `inventory_bp = Blueprint("inventory", __name__)` in `routes/inventory_routes.py` and `workflow_bp = Blueprint("workflow", __name__)` in `routes/workflow_routes.py`.
- Register blueprints centrally in `create_app()` in `app.py`; do not register blueprints inside individual route modules.
- Keep extension singletons in `core/extensions.py` and bind them in `create_app()` in `app.py`.

**Service Modules:**
- Keep business logic in `core/services/*.py`, as in `core/services/workflow_service.py`, `core/services/inventory_tx_service.py`, `core/services/product_service.py`, and `core/services/wallet_service.py`.
- Do not import `request`, `current_user`, or `jsonify` into service modules; keep those in route modules such as `routes/workflow_routes.py` and `routes/inventory_routes.py`.
- Use `core/services/service_errors.py` for service errors that routes translate to HTTP responses.

**Repository Modules:**
- Keep table-specific reusable SQL in `core/db/*.py`, as in `core/db/user_repo.py`, `core/db/workflow_repo.py`, `core/db/activity_repo.py`, and `core/db/chat_repo.py`.
- Keep connection factory and SQLite/PostgreSQL compatibility logic in `core/database.py`; do not duplicate placeholder conversion in service modules.

**Frontend Modules:**
- Link page-specific scripts through the template `scripts` block, as in `ui/templates/admin_dashboard.html`, `ui/templates/admin_managers.html`, and `ui/templates/admin_roles.html`.
- Use page-local browser globals and `DOMContentLoaded` initializers in `static/js/*.js`, as in `static/js/admin_products.js`, `static/js/admin_dashboard.js`, and `static/js/wallet.js`.
- Keep API field names in JavaScript payloads aligned with backend snake_case fields, as in `static/js/admin_imports.js`, `static/js/admin_exports.js`, and `static/js/admin_products.js`.

## Planning Artifact Conventions

- Codebase map documents live under `.planning/codebase/` per `.codex/skills/gsd-map-codebase/SKILL.md`.
- Planning and execution artifacts under `.planning/` use path-rich references to source files, as shown in `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`, and `.planning/phases/12-service-boundary-extraction/12-CONTEXT.md`.
- Future implementation agents should use these codebase map documents as prescriptive guidance and update only the relevant `.planning/codebase/*.md` files when conventions drift.

---

*Convention analysis: 2026-06-08*
