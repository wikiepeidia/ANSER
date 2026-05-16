# Coding Conventions

**Analysis Date:** 2026-05-16

## Naming Patterns

**Files:**
- snake_case for all Python modules: `auth.py`, `database.py`, `workflow_engine.py`
- Service files follow `<noun>_service.py` pattern: `product_service.py`, `inventory_tx_service.py`, `ai_chat_service.py`
- Route Blueprint files follow `<noun>_routes.py` pattern: `main_routes.py`, `ai_routes.py`, `inventory_routes.py`
- Utility files follow descriptive names: `service_errors.py`, `extensions.py`, `helpers.py`

**Functions:**
- snake_case throughout: `get_all_products()`, `create_import_transaction()`, `normalize_message()`
- Private helper functions prefixed with underscore: `_decode_google_token()`, `_configure_oauth()`, `_app_module()`
- Description-based naming with verb prefix: `get_`, `create_`, `update_`, `delete_`, `fetch_`, `resolve_`, `submit_`

**Variables:**
- snake_case for regular variables: `user_id`, `workflow_data`, `db_conn`
- UPPER_CASE for module-level constants: `PROJECT_ROOT`, `ALLOWED_EXTENSIONS`, `_GREETINGS`
- Single-letter iteration variables acceptable: `r` (in list comprehensions), `e` (in except)

**Classes:**
- PascalCase: `Database`, `Config`, `AuthManager`, `AutomationEngine`, `AgentMiddleware`
- Shim classes prefixed with context: `PGShimCursor`, `PGShimConnection`
- Service error classes follow `Service<Type>Error` pattern: `ServiceValidationError`, `ServiceAuthorizationError`, `ServiceInvariantError`

**Blueprint objects:**
- Lowercase with `_bp` suffix: `main_bp`, `inventory_bp`, `workflow_bp`
- Blueprint name string uses abbreviated module name: `Blueprint('main', __name__)`

## Code Style

**Formatting:**
- No formatter enforced (no `.prettierrc`, `pyproject.toml` formatter section, or `setup.cfg`)
- Observed: 4-space indentation (Python standard, consistent throughout)
- Blank line between methods and logical sections
- Section headers for long functions using dashes: `# ── Customers ──────────────────────────────────────────────────────────────`

**Linting:**
- No linting config detected (no `.flake8`, `pylint.ini`, `ruff.toml`)
- Follow PEP 8 as implicit standard

**String Formatting:**
- f-strings are the dominant pattern: `f"Processing {file.filename}"`, `f"Error: {e}"`
- Old-style `.format()` or `%` formatting not present in core/routes files
- Triple-quoted strings for SQL: `'''INSERT INTO products ...'''`

## Import Organization

**Order (observed convention):**
1. Standard library: `import os`, `import json`, `import threading`
2. Third-party frameworks: `from flask import ...`, `from flask_login import ...`
3. Internal core modules: `from core.extensions import ...`, `from core.services import ...`
4. Relative imports within a package: `from .service_errors import ServiceValidationError`

**Pattern example** (from `routes/main_routes.py`):
```python
from flask import Blueprint, flash, jsonify, redirect, request, url_for
from flask_login import current_user, login_required, logout_user

from core.services.customer_service import (
    create_customer, delete_customer, get_all_customers, update_customer,
)
from core.services.product_service import (
    create_product, delete_product, get_all_products, import_products_from_excel,
    update_product,
)
```

**Path style:**
- Root-relative absolute imports used in routes and core: `from core.config import Config`
- Relative imports used within `core/services/` package: `from .service_errors import ServiceValidationError`
- `src.` prefix is NOT used in the main app (that prefix appears only in `ai_agent_service/` subdirectory)
- No path aliases configured (`@/` or `~/` equivalents not present)

**Circular import avoidance:**
- Extensions declared as module-level singletons in `core/extensions.py` without Flask app
- Lazy import pattern for circular cases: `def _app_module(): import app as app_module; return app_module`

## Error Handling

**Service-layer exceptions** (use these in all `core/services/` files):
```python
from .service_errors import ServiceValidationError, ServiceAuthorizationError, ServiceInvariantError

# Raise on bad input
raise ServiceValidationError("user_id is required")

# Raise on business rule violation
raise ServiceInvariantError("Insufficient stock")
```

**Route-layer exception handling** (translate service errors to HTTP responses):
```python
try:
    result = some_service.do_thing(conn, user_id, data)
    return jsonify({'success': True, 'message': result['message'], 'id': result['id']})
except ServiceValidationError as e:
    return jsonify({'success': False, 'message': str(e)}), 400
except ServiceInvariantError as e:
    return jsonify({'success': False, 'message': str(e)}), 500
except Exception as e:
    return jsonify({'success': False, 'message': str(e)}), 500
finally:
    conn.close()
```

**Avoid bare except** clauses (legacy pattern in `core/database.py` and `core/agent_middleware.py` — do not replicate):
```python
# BAD (legacy, found in core/agent_middleware.py)
except:
    pass

# GOOD
except Exception as e:
    print(f"[Module] Error: {e}")
```

**JSON API response shape** — use consistently:
```python
# Success
return jsonify({'success': True, 'message': '...', 'data': ...})

# Failure
return jsonify({'success': False, 'message': '...'}), 4xx
```

## Logging

**Main app and core (`core/`):**
- No structured logger — uses `print()` with bracket-prefixed module tags:
  ```python
  print("[Automation] Engine started")
  print(f"[Google] Error loading token: {e}")
  print(f"[Automation] Error in scheduler: {e}")
  ```
- Emoji prefix for severity in database operations:
  ```python
  print(f"⚠️ Memory Save Error: {e}")
  print(f"❌ DB Attachment Error: {e}")
  ```

**Deep learning service (`dl_service/`):**
- Uses structured `get_logger` from `dl_service/utils/logger.py`:
  ```python
  from dl_service.utils.logger import get_logger
  logger = get_logger(__name__)
  logger.info("Processing request")
  logger.error(f"Inference failed: {e}")
  ```
- This pattern is the target standard; `print()` in `core/` is legacy.

**Rule:** Use `print("[Module] message")` in `core/` and `routes/` for now. Never silently swallow errors — always log.

## Comments

**When to use:**
- Section headers in long files: `# ── Authentication ──────────────`
- Non-obvious logic: `# FIX: attn_implementation="eager" fixes the _supports_sdpa crash`
- Configuration explanations: `# Give 50% (40GB) to the 32B model`
- Compatibility shims: `# Only init if not Postgres to avoid schema conflicts`

**Docstrings:**
- Module-level docstring required in service modules: `"""Workflow service functions extracted from route handlers."""`
- Function docstrings for public service functions: `"""Execute workflow with token decoding delegated from the route layer."""`
- Not required for simple route handlers

**Prohibited:**
- Commented-out code (track deferred work in `TODO.md` instead)
- `TODO` comments in production code (use `TODO.md`)

## Function Design

**Size:**
- Service functions: 10–30 lines typical
- Route handlers: 15–40 lines typical
- Helper/private functions: 5–15 lines

**Parameters:**
- Inject `db_conn` as first parameter in service functions (enables testability without Flask context):
  ```python
  def create_import_transaction(conn, user_id, payload):
  ```
- Use `**kwargs` for optional parameters in engine/model calls

**Return values:**
- Service functions return plain dicts: `{'message': '...', 'id': row_id}`
- Boolean + error tuple for CRUD that can fail: `return True, None` / `return False, 'error message'`
- List of dicts for collection queries: `[{'id': r[0], 'name': r[1], ...} for r in rows]`
- Always return something meaningful — avoid implicit `None`

## Module Design

**One main class per module** (when class-based):
- `core/database.py` exports `Database`
- `core/auth.py` exports `AuthManager`
- `core/automation_engine.py` exports `AutomationEngine`

**Service modules are function-based** (no class wrapper):
- `core/services/product_service.py` exports `get_all_products`, `create_product`, etc.
- `core/services/workflow_service.py` exports `execute_user_workflow`, `list_workflows_for_user`

**Blueprint + Service pattern** (required for all new routes):
```
routes/<noun>_routes.py       ← Blueprint, @login_required, jsonify, HTTP error codes
core/services/<noun>_service.py ← Pure Python, no Flask globals, accepts db_conn as arg
```
- Routes handle: request parsing, auth, HTTP response formatting, connection lifecycle
- Services handle: business logic, validation, DB writes, raising ServiceXxxError

**Singleton pattern** for shared infrastructure:
- `core/extensions.py` holds `db_manager`, `login_manager`, `csrf`, `limiter` as module-level singletons
- `db_manager = Database()` instantiated once at import time
- Flask extensions initialized via `init_app()` inside `create_app()`

## Configuration Management

**Centralized Config class** in `core/config.py`:
```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change_me_random_key')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'group_project_ai_ml.db')
    POSTGRES_URL = os.environ.get('POSTGRES_URL')
    USE_POSTGRES = bool(POSTGRES_URL) or os.environ.get('USE_POSTGRES', 'False').lower() == 'true'
```

**Rules:**
- Always use `os.environ.get('VAR', 'default')` — never hardcode production values
- Load `.env` at module top via `load_dotenv()` (called in `core/config.py`)
- Secrets in `secrets/` directory, loaded conditionally — never committed to git
- Feature flags via env: `USE_POSTGRES`, `RATELIMIT_ENABLED`
- Flask app config set inside `create_app()`, not at module level

---

*Convention analysis: 2026-05-16*
