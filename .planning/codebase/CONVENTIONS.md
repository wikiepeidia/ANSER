# Coding Conventions

**Analysis Date:** 2026-07-08

## Naming Patterns

**Files:**
- Snake_case Python modules: `product_service.py`, `inventory_tx_service.py`, `workflow_repo.py`
- Route modules grouped by domain in `routes/`: `inventory_routes.py`, `ai_routes.py`, `admin_user_routes.py`, `admin_subscription_routes.py`
- Service layer modules live in `core/services/*.py`, one file per domain (`customer_service.py`, `sales_service.py`, `wallet_service.py`, `subscription_service.py`, `workspace_service.py`, `analytics_service.py`, `ai_chat_service.py`, `dl_client.py`, `operations_service.py`, `user_service.py`, `inventory_tx_service.py`, `service_errors.py`)
- Test files mirror source under `tests/`: `tests/services/test_ai_chat_service.py`, `tests/test_workflow_crud.py`, `tests/services/test_inventory_tx_service.py`

**Functions:**
- snake_case throughout: `get_all_products`, `create_product`, `delete_sale`, `detect_column_mapping`
- Private/internal helpers prefixed with a single underscore: `_can_access_all`, `_normalize_col`, `_get_next_sp_number`, `_make_mem_conn` (see `core/services/product_service.py`)
- CRUD-style service functions named `get_all_X`, `create_X`, `update_X`, `delete_X` per domain (e.g. `core/services/product_service.py:92,132,149,168`)

**Variables:**
- snake_case for locals and parameters: `warehouse_id`, `created_by`, `stock_quantity`
- Module-level constants in UPPER_SNAKE or leading-underscore UPPER for internal constants: `FIELD_LABELS` (public), `_FIELD_KEYWORDS`, `_PREFIX_RE` (`core/services/product_service.py:7-30`)

**Types/Classes:**
- PascalCase for classes: `AuthManager`, `AutomationEngine`, `Database`, `AnalyticsService`, `WorkflowRepo`
- Custom service exceptions suffixed `Error`: `ServiceValidationError`, `ServiceAuthorizationError`, `ServiceInvariantError` (`core/services/service_errors.py`)

## Code Style

**Formatting:**
- No `.prettierrc`/`black` config detected; code style is implicit/hand-maintained. 4-space indentation is used consistently (per `CLAUDE.md` project instruction).
- Some modules use aligned dict literals for readability (e.g. `FIELD_LABELS` / `_FIELD_KEYWORDS` in `core/services/product_service.py`).

**Linting:**
- `ruff>=0.4.0` is listed in `requirements-dev.txt` as the lint tool, but no `ruff.toml` or `[tool.ruff]` section was found in a `pyproject.toml` — linting rules are effectively default/unconfigured. Run `ruff check .` manually; do not assume a project-specific ruleset exists.

**Docstrings:**
- Module and function docstrings are frequently written in **Vietnamese**, matching the bilingual team (e.g. `core/services/service_errors.py`, `core/services/product_service.py`). New code should follow existing file's language convention rather than force English everywhere — check neighboring docstrings before adding new ones.
- Docstrings use triple-quoted `"""..."""`, often single summary line plus optional `Returns:` block for non-trivial functions (`core/services/product_service.py:45-52`).

## Import Organization

**Order:**
1. Standard library (`import re`, `import sqlite3`, `import io`, `import json`)
2. Third-party packages (`import pandas as pd`, `import pytest`)
3. Local/project imports (`from core.auth import AuthManager`, `from core.services.service_errors import ServiceValidationError`)

No `isort` config detected; ordering is manual convention observed across files (`core/services/product_service.py:1-5`, `tests/test_security_hardening.py:1-21`).

**Path Aliases:**
- None. Imports are absolute from repo root (`pytest.ini` sets `pythonpath = .`), e.g. `from core.db.workflow_repo import WorkflowRepo`, `from routes.inventory_routes import ...`.

## Error Handling

**Domain/service layer:**
- Custom exceptions defined in `core/services/service_errors.py`:
  - `ServiceValidationError` — invalid input data
  - `ServiceAuthorizationError` — caller lacks permission
  - `ServiceInvariantError` — business rule violated during processing
- Also used: built-in `LookupError` (not-found / wrong-owner lookups, e.g. `core/services/sales_service.py` raising `LookupError` on `delete_sale` when the caller isn't the owner — see `tests/test_security_hardening.py:35`), and `PermissionError` (authorization failures in `routes/admin_user_routes.py`), and `ValueError` for basic input validation (`routes/admin_subscription_routes.py`, `routes/dl_routes.py`).

**Route layer:**
- Routes catch the specific service exceptions and translate them to HTTP responses, e.g. `routes/inventory_routes.py`:
  ```python
  except ServiceValidationError as e:
      ...
  except ServiceInvariantError as e:
      ...
  ```
  and `routes/admin_user_routes.py`:
  ```python
  except LookupError as e:
      ...
  except PermissionError as e:
      ...
  ```
- Pattern: catch narrow, specific exception types close to the route handler rather than broad `except Exception`. Follow this pattern for new routes — import the relevant `Service*Error` from `core.services.service_errors` and add a dedicated `except` clause per error type, mapping to the correct HTTP status code.

**Ownership/authorization checks:**
- Service functions accept `user_id`/`role` and enforce row ownership by raising `LookupError` when a record doesn't belong to the caller, rather than silently returning `None` (see `core/services/sales_service.py:delete_sale`, verified in `tests/test_security_hardening.py:30-41`).

## Logging

**Framework:** Custom centralized logger in `core/logger.py`.

**Usage pattern:**
```python
from core.logger import get_logger
logger = get_logger(__name__)
```
Adopted in `core/agent_middleware.py`, `core/auth.py`, `core/automation_engine.py`, `core/excel_parser.py`, `core/google_integration.py`, `core/make_integration.py`.

**Implementation details** (`core/logger.py`):
- JSON-formatted log lines via a custom `_JsonFormatter` (fields: `time`, `level`, `name`, `message`, `exc_info`) — no third-party logging library.
- `RotatingFileHandler` writes to `logs/app.log` (max 5 MB, 3 backups); also streams to console.
- One shared handler pair per process (thread-safe).

**Rule enforced by tests:** No `print()` calls in service modules — `tests/test_code_hygiene.py::test_analytics_service_has_no_print_calls` asserts `"print(" not in source` for `core/services/analytics_service.py`. Treat this as a repo-wide expectation: use `logger` instead of `print` in `core/` and `core/services/`.

## Testing-Adjacent Hygiene Rules

`tests/test_code_hygiene.py` encodes conventions as executable assertions — treat these as binding style rules, not just tests:
- No bare `print()` in service code (inspects `inspect.getsource(...)`).
- No raw tuple-index access into `sqlite3.Row`-like objects (`workspace[3]`, `workspace[0]`, etc.) — use named/dict-style field access instead (`Utils.format_workspace_tree` is the enforced example, `tests/test_code_hygiene.py:75-81`).
- SQL query string construction that includes user input must be escaped (see `test_google_drive_query_escapes_single_quotes` for the Google Drive integration's quote-escaping requirement, `tests/test_code_hygiene.py:27-47`).

## Function Design

**Size:** Functions tend to be small and single-purpose in the service layer; larger multi-step functions (e.g. `detect_column_mapping` in `core/services/product_service.py`) are still self-contained within one file and rely on private module-level helpers (`_normalize_col`) for sub-steps.

**Parameters:** Service functions consistently take a raw `conn` (sqlite3 connection) as the first parameter, followed by domain fields, then `user_id`/`role`/`created_by` for ownership/authorization context — e.g. `create_product(conn, code, name, category, unit, price, stock_quantity, description, created_by, image_url='')` (`core/services/product_service.py:132`).

**Return Values:** Functions generally return plain dicts/lists (rows converted from `sqlite3.Row`) rather than custom DTOs/dataclasses; no ORM layer — raw SQL via `sqlite3` cursors throughout the service layer.

## Module Design

**Exports:** No `__all__` conventions observed; modules export via plain top-level function/class definitions. Services are imported directly by dotted path (`from core.services.customer_service import delete_customer, get_all_customers, update_customer`).

**Repository pattern:** Data-access classes named `*Repo` wrap raw SQL for a given table/domain (e.g. `core.db.workflow_repo.WorkflowRepo` in `core/db/workflow_repo.py`), separate from the `*_service.py` business-logic layer. New domains should follow this two-layer split: `core/db/<domain>_repo.py` for SQL, `core/services/<domain>_service.py` for validation/business rules, `routes/<domain>_routes.py` for HTTP glue.

**Bilingual comments:** Business-domain modules (product mapping/import, inventory) mix Vietnamese comments/docstrings with English code — this reflects the Vietnamese-speaking dev team and is intentional; match the existing language of the file you're editing.

---

*Convention analysis: 2026-07-08*
