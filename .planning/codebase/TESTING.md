# Testing Patterns

**Analysis Date:** 2026-05-16

## Test Framework

**Runner:**
- pytest >= 8.0.0
- Config: `pytest.ini` (project root)
- `testpaths = tests`, `python_files = test_*.py`, `pythonpath = .`, `addopts = -q`

**Assertion Library:**
- pytest built-in assertions + `pytest.raises`, `pytest.approx`

**Additional libraries** (from `requirements-dev.txt`):
- `pytest-cov >= 5.0.0` — coverage reporting
- `pytest-mock >= 3.14.0` — `monkeypatch` fixture
- `pytest-timeout >= 2.3.1` — per-test timeouts
- `requests-mock >= 1.12.1` — HTTP mocking (available but not yet used in existing tests)

**Run Commands:**
```bash
pytest                           # Run all tests (quiet mode via addopts = -q)
pytest tests/services/           # Run service unit tests only
pytest tests/contracts/          # Run contract/route tests only
pytest tests/integration/        # Run integration tests only
pytest --cov=core --cov-report=term-missing  # With coverage
pytest -v                        # Verbose output
```

## Test File Organization

**Location:** All tests under `tests/` directory (not colocated with source)

**Structure:**
```
tests/
├── conftest.py                          # Session-scoped app + client fixtures
├── contracts/
│   ├── test_contract_routes.py          # Route registry contracts (app.url_map checks)
│   └── test_contract_smoke.py           # HTTP smoke tests driven by endpoint manifest JSON
├── integration/
│   └── test_catalog_crud_smoke.py       # Full HTTP CRUD for products + customers
└── services/
    ├── conftest.py                      # Shared stubs: _DBStub, workflow_payload, tx_payload
    ├── test_ai_chat_service.py          # Unit tests for ai_chat_service functions
    ├── test_extraction_contracts.py     # Service boundary: no Flask globals, callable contracts
    ├── test_inventory_route_delegation.py  # Route→service delegation via monkeypatch
    ├── test_inventory_tx_service.py     # Unit tests with in-memory SQLite
    ├── test_product_import.py           # Unit tests for Excel import with stub DB
    └── test_workflow_service.py         # Unit tests for workflow service functions
```

**Naming:**
- File: `test_<module_or_feature>.py`
- Function: `test_<behaviour_under_test>` (e.g., `test_create_import_transaction_calculates_total_and_increments_stock`)

## Test Structure

**Suite organization:**
```python
"""Unit tests for inventory transaction service behavior."""

import pytest
import core.services.inventory_tx_service as inventory_tx_service
from core.services.service_errors import ServiceValidationError


def test_create_import_transaction_calculates_total_and_increments_stock():
    conn = _new_conn()
    # ... arrange
    result = inventory_tx_service.create_import_transaction(conn, user_id=9, payload={...})
    assert result["message"] == "Import created successfully"
    # ... assert DB side-effects
```

- No `class`-based test grouping — all tests are plain functions at module level
- Local helper functions (prefixed `_`) for shared setup within a test file
- `conftest.py` fixtures for cross-file shared infrastructure

**Setup patterns:**
- In-memory SQLite via `sqlite3.connect(":memory:")` with schema creation helpers (`_new_conn()`)
- Stub classes defined inline or in `conftest.py` (`_DBStub`, `_CursorStub`, `_ConnStub`)
- `monkeypatch.setattr` for replacing module-level dependencies

**Teardown:**
- `tmp_path` fixture (pytest built-in) for temporary SQLite file databases in integration tests
- `finally:` blocks in fixtures restore original `db_manager` attributes after tests

## Mocking

**Framework:** `pytest` built-in `monkeypatch` (no `unittest.mock` usage detected)

**Patterns:**

Replace a module-level function:
```python
def test_execute_user_workflow_parses_google_token_json(monkeypatch, workflow_payload):
    def _fake_execute(workflow_data, token_info):
        return {"status": "ok"}
    monkeypatch.setattr(workflow_service, "execute_workflow", _fake_execute)
```

Replace a dependency on another module:
```python
monkeypatch.setattr(product_service.db_manager, 'get_connection', lambda: conn)
```

Replace app-level globals for route delegation tests:
```python
monkeypatch.setattr(app_module, "current_user", SimpleNamespace(id=55))
monkeypatch.setattr(app_module, "db_manager", _DbManagerStub(conn))
monkeypatch.setattr(inventory_routes.inventory_tx_service, "create_import_transaction", _fake_fn)
```

**Stub class pattern** (used throughout `tests/services/`):
```python
class _CursorStub:
    def __init__(self):
        self.lastrowid = 1
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return []

    def fetchone(self):
        return (5,)

class _DBStub:
    def __init__(self):
        self._cursor = _CursorStub()

    def cursor(self):
        return self._cursor

    def commit(self):
        return None

    def rollback(self):
        return None
```

**What to mock:**
- `db_manager.get_connection` to inject test connections
- Flask `current_user` when testing route delegation
- External service calls (workflow engine, automation engine) in service unit tests

**What NOT to mock:**
- `sqlite3` itself in integration tests — use real in-memory SQLite
- Service functions when testing routes via integration tests — exercise the real call chain

## Fixtures and Factories

**Session fixtures** (`tests/conftest.py`):
```python
@pytest.fixture(scope="session")
def app():
    flask_app = getattr(app_module, "app", None)
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    return flask_app

@pytest.fixture()
def client(app):
    return app.test_client()
```

**Shared service fixtures** (`tests/services/conftest.py`):
```python
@pytest.fixture
def db_stub():
    return _DBStub()          # Minimal cursor/connection stub

@pytest.fixture
def workflow_payload():
    return {"nodes": [], "edges": []}

@pytest.fixture
def tx_payload():
    return {"items": [{"product_id": 1, "quantity": 2, "unit_price": 10.0}]}
```

**Integration fixture** (tmp SQLite + patched db_manager):
```python
@pytest.fixture()
def catalog_client(app, tmp_path):
    db_path = tmp_path / 'catalog-smoke.db'
    old_db_path = db_manager.db_path
    db_manager.db_path = str(db_path)
    db_manager.use_postgres = False
    _create_test_schema(str(db_path))
    try:
        with app.test_client() as client:
            with client.session_transaction() as session:
                session['_user_id'] = '1'   # Simulate logged-in user
                session['_fresh'] = True
            yield client, str(db_path)
    finally:
        db_manager.db_path = old_db_path   # Always restore
```

**Excel factory helper** (`tests/services/test_product_import.py`):
```python
def _make_excel(rows, headers=None):
    """Build an in-memory .xlsx file with given headers and rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers or ['code', 'name', 'category', 'unit', 'price', 'stock_quantity'])
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = 'test.xlsx'
    return buf
```

## Coverage

**Requirements:** No enforced minimum (no `--cov-fail-under` in `pytest.ini`)

**View coverage:**
```bash
pytest --cov=core --cov-report=term-missing
pytest --cov=routes --cov-report=term-missing
pytest --cov=core --cov=routes --cov-report=html
```

## Test Types and What Is Covered

**Unit tests** (`tests/services/`):
- `test_ai_chat_service.py` — greeting resolution, message normalization, history formatting
- `test_inventory_tx_service.py` — import/export transaction creation with real in-memory SQLite
- `test_product_import.py` — Excel file import: insert, update, skip, error, missing column
- `test_workflow_service.py` — workflow CRUD, token parsing, validation

**Contract/boundary tests** (`tests/services/test_extraction_contracts.py`):
- Verify service modules expose required callable interfaces
- Verify service modules contain no Flask globals (`request`, `current_user`)

**Route delegation tests** (`tests/services/test_inventory_route_delegation.py`):
- Verify routes pass correct arguments to service functions
- Verify connections are closed in `finally` block

**Route registry contracts** (`tests/contracts/test_contract_routes.py`):
- Verify all routes in endpoint manifest JSON exist in Flask `url_map`
- Verify route methods match manifest specification
- Smoke-tests for sales, workspace, admin-user, analytics, and subscription route groups

**HTTP smoke tests** (`tests/contracts/test_contract_smoke.py`):
- Parameterized smoke requests driven by `.planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json`
- Tests groups: `workflow`, `ai`, `import_export`
- Tests page routes: home, dashboard, imports, exports

**Integration tests** (`tests/integration/test_catalog_crud_smoke.py`):
- Full HTTP CRUD cycle for products and customers using real SQLite + seeded data
- Tests: list, create, update, delete, duplicate rejection

## Test Coverage Gaps

**Authentication flows — NOT tested:**
- Login, logout, Google OAuth callback routes (`routes/auth_routes.py`, `routes/google_routes.py`)
- Password reset, token expiry, session refresh
- Risk: auth regressions invisible until manual testing or production failure

**AI/LLM chat path — NOT tested end-to-end:**
- `routes/ai_routes.py` job creation, job polling, DL service integration
- The `AgentMiddleware` invocation chain is not covered
- Risk: demo failure if LLM path breaks silently

**Wallet and subscription — NOT tested:**
- `routes/wallet_routes.py`, `routes/admin_subscription_routes.py`
- `core/services/wallet_service.py`, `core/services/subscription_service.py`
- Risk: billing features untested before jury demo

**Analytics and reporting — NOT tested:**
- `routes/operations_routes.py`, Google Analytics integration in `core/google_integration.py`
- `core/services/analytics_service.py` (complex, 165+ lines with nested try/except)
- Risk: dashboard may break if GA service account is misconfigured

**Sales routes — partially tested (registry only):**
- `routes/sales_routes.py` routes are contract-verified (registry check) but no HTTP behavior tests
- `core/services/sales_service.py` has zero test coverage

**DL service — NOT tested from main app:**
- `dl_service/` models, OCR pipeline, forecast service have no tests in `tests/`
- The `DLClient` in `core/services/dl_client.py` is untested

**Workflow engine execution — NOT tested:**
- `core/workflow_engine.py` (472 lines) has no direct tests
- Node dispatch, DAG topological sort, template variable resolution untested

**Admin user management — registry only:**
- `routes/admin_user_routes.py` route paths are contract-verified but no behavior tests
- User creation, deletion, role promotion untested at HTTP layer

## Common Patterns

**Async/exception testing:**
```python
def test_create_export_transaction_rolls_back_on_insufficient_stock():
    with pytest.raises(ServiceValidationError):
        inventory_tx_service.create_export_transaction(conn, user_id=12, payload={...})
    # Assert DB state unchanged after rollback
    assert conn.execute("SELECT COUNT(*) FROM export_transactions").fetchone()[0] == 0
```

**Parametrized tests:**
```python
@pytest.mark.parametrize("message", ["xin chào", "hello", "hi", "chào"])
def test_resolve_greeting_reply_matrix(message):
    reply = ai_chat_service.resolve_greeting_reply(message)
    assert isinstance(reply, str)
    assert "trợ lý ảo" in reply
```

**Route test request context:**
```python
def _call_wrapped(route_fn, path, payload):
    wrapped = getattr(route_fn, "__wrapped__", route_fn)
    with app_module.app.test_request_context(path, method="POST", json=payload):
        return wrapped()
```

**Database side-effect verification:**
```python
# Check DB state after service call
stock_quantity = conn.execute(
    "SELECT stock_quantity FROM products WHERE id = 1"
).fetchone()[0]
assert stock_quantity == 8
```

---

*Testing analysis: 2026-05-16*
