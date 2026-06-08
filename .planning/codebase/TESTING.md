# Testing Patterns

**Analysis Date:** 2026-06-08

## Test Framework

**Runner:**
- pytest `>=8.0.0` from `requirements-dev.txt`.
- Config: `pytest.ini`.
- Test discovery is limited to `tests/` by `testpaths = tests` in `pytest.ini`.
- Test file pattern is `test_*.py` by `python_files = test_*.py` in `pytest.ini`.
- Repository-root imports are enabled by `pythonpath = .` in `pytest.ini`.
- Quiet output is enabled by `addopts = -q` in `pytest.ini`.

**Assertion Library:**
- Use plain Python `assert` statements with pytest assertion rewriting, as in `tests/services/test_inventory_tx_service.py`, `tests/test_inventory.py`, and `tests/contracts/test_contract_routes.py`.
- Use `pytest.raises(...)` for expected exceptions, as in `tests/services/test_inventory_tx_service.py`, `tests/test_inventory.py`, and `tests/test_ops_subscription.py`.
- Use `pytest.approx(...)` for float comparisons, as in `tests/services/test_inventory_tx_service.py`, `tests/test_inventory.py`, and `tests/test_ops_subscription.py`.
- Use Flask test client response assertions, as in `tests/integration/test_catalog_crud_smoke.py`, `tests/contracts/test_contract_smoke.py`, and `tests/parity/test_endpoint_middleware_parity.py`.

**Run Commands:**
```bash
python -m pytest                         # Run all configured tests under `tests/`
python -m pytest tests/services -q       # Run service-layer tests
python -m pytest tests/contracts -q      # Run route contract/smoke tests
python -m pytest tests/parity -q         # Run parity tests
python -m pytest tests/integration -q    # Run integration smoke tests
```

**Watch Mode:**
```bash
# Not detected: no pytest-watch, nodemon, npm test, or watch script is configured in `requirements-dev.txt` or `package.json`.
```

**Coverage:**
```bash
python -m pytest tests/services tests/contracts -q --cov=app --cov=core --cov=routes --cov-config=.coveragerc --cov-report=term-missing:skip-covered --cov-fail-under=20
```

## Test File Organization

**Location:**
- Put configured pytest tests under `tests/`, because `pytest.ini` sets `testpaths = tests`.
- Put service-unit tests under `tests/services/`, as in `tests/services/test_workflow_service.py`, `tests/services/test_ai_chat_service.py`, `tests/services/test_inventory_tx_service.py`, and `tests/services/test_product_import.py`.
- Put route registry and smoke contract tests under `tests/contracts/`, as in `tests/contracts/test_contract_routes.py` and `tests/contracts/test_contract_smoke.py`.
- Put parity tests under `tests/parity/`, as in `tests/parity/test_endpoint_middleware_parity.py` and `tests/parity/test_data_async_parity.py`.
- Put Flask client integration smoke tests under `tests/integration/`, as in `tests/integration/test_catalog_crud_smoke.py`.
- Root-level `tests/test_*.py` files cover broader service/repository integration slices, as in `tests/test_auth_integration.py`, `tests/test_inventory.py`, `tests/test_ops_subscription.py`, `tests/test_services_extra.py`, and `tests/test_workflow_crud.py`.
- `debug/test_login.py`, `dl_service/test_vietocr.py`, `dl_service/test_vietocr2.py`, and `dl_service/test_ocr_pipeline.py` are outside configured `pytest.ini` discovery and should be treated as manual/ad hoc scripts unless moved under `tests/`.

**Naming:**
- Use file names starting with `test_`, as in `tests/services/test_inventory_tx_service.py`, `tests/contracts/test_contract_routes.py`, and `tests/parity/test_data_async_parity.py`.
- Use test function names starting with `test_`, as in `test_create_import_transaction_calculates_total_and_increments_stock()` in `tests/services/test_inventory_tx_service.py`.
- Use fixture names that describe the provided dependency, as in `app`, `client`, and `sqlite_db` in `tests/conftest.py`; `db_stub`, `workflow_payload`, and `tx_payload` in `tests/services/conftest.py`; and `catalog_client` in `tests/integration/test_catalog_crud_smoke.py`.
- Use private helper names with a leading underscore, as in `_make_conn()` in `tests/test_inventory.py`, `_new_conn()` in `tests/services/test_inventory_tx_service.py`, and `_load_manifest()` in `tests/contracts/test_contract_routes.py`.

**Structure:**
```text
tests/
├── conftest.py                         # Flask app/client and temp SQLite fixtures
├── contracts/                          # Endpoint manifest and smoke guardrails
├── integration/                        # Flask client + temporary DB smoke tests
├── parity/                             # Middleware, DB mode, and async lifecycle parity tests
├── services/                           # Service-layer unit tests and shared service fixtures
└── test_*.py                           # Broader service/repository integration tests
```

## Test Structure

**Suite Organization:**
```python
# Pattern from `tests/services/test_inventory_tx_service.py`
import sqlite3

import pytest

import core.services.inventory_tx_service as inventory_tx_service
from core.services.service_errors import ServiceValidationError


def _new_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("...")
    conn.commit()
    return conn


def test_create_export_transaction_rolls_back_on_insufficient_stock():
    conn = _new_conn()
    with pytest.raises(ServiceValidationError):
        inventory_tx_service.create_export_transaction(conn, user_id=12, payload={...})
```

**Patterns:**
- Define local SQLite schema helpers inside the test file when the schema is specific to one module, as in `_new_conn()` in `tests/services/test_inventory_tx_service.py` and `_make_conn()` in `tests/test_inventory.py`.
- Put shared service fixtures in `tests/services/conftest.py` when multiple service tests need the same schema or payload.
- Use `tests/conftest.py` for app-level fixtures (`app`, `client`, `sqlite_db`) used by contract and integration tests.
- Use `pytest.mark.parametrize` for endpoint matrices and input variants, as in `tests/integration/test_catalog_crud_smoke.py`, `tests/contracts/test_contract_smoke.py`, and `tests/parity/test_endpoint_middleware_parity.py`.
- Use direct function calls for service tests instead of Flask test requests, as in `tests/services/test_workflow_service.py`, `tests/services/test_ai_chat_service.py`, and `tests/services/test_inventory_tx_service.py`.
- Use Flask `client` or `app.test_client()` only for route, contract, parity, and integration tests, as in `tests/contracts/test_contract_smoke.py`, `tests/parity/test_endpoint_middleware_parity.py`, and `tests/integration/test_catalog_crud_smoke.py`.

## Mocking

**Framework:** pytest `monkeypatch`; `pytest-mock` is installed in `requirements-dev.txt` but no `mocker` fixture usage is detected in `tests/`.

**Patterns:**
```python
# Pattern from `tests/services/test_inventory_route_delegation.py`
from types import SimpleNamespace

def test_api_create_import_delegates_to_inventory_service(monkeypatch):
    conn = _ConnStub()
    called = {}

    def _fake_create_import(db_conn, user_id, payload):
        called["db_conn"] = db_conn
        called["user_id"] = user_id
        called["payload"] = payload
        return {"message": "Import created successfully", "id": 101}

    monkeypatch.setattr(app_module, "current_user", SimpleNamespace(id=55))
    monkeypatch.setattr(app_module, "db_manager", _DbManagerStub(conn), raising=False)
    monkeypatch.setattr(inventory_routes.inventory_tx_service, "create_import_transaction", _fake_create_import)
```

**What to Mock:**
- Mock Flask globals and app singletons when testing route delegation directly, as in `tests/services/test_inventory_route_delegation.py`.
- Mock external email sending, as in `tests/test_auth_integration.py` patching `core.auth.send_email`.
- Mock outbound HTTP and background dependencies, as in `tests/parity/test_data_async_parity.py` patching `ai_routes.requests.post`, `ai_routes.Database`, and `ai_routes.AgentMiddleware`.
- Mock `db_manager` with a real in-memory SQLite connection wrapper for services that import the singleton, as in `tests/test_services_extra.py` and `tests/test_ops_subscription.py`.
- Use local stub classes for cursor/connection behavior when the test only needs call recording, as in `tests/services/test_product_import.py` and `tests/parity/test_data_async_parity.py`.

**What NOT to Mock:**
- Do not mock service functions when the test target is service behavior; use real SQLite connections in `tests/services/test_inventory_tx_service.py`, `tests/test_inventory.py`, and `tests/test_workflow_crud.py`.
- Do not mock Flask route registration for contract tests; use `app.url_map` in `tests/contracts/test_contract_routes.py`.
- Do not mock the `AuthManager` database path in auth integration tests beyond the temporary SQLite fixture in `tests/conftest.py`; `tests/test_auth_integration.py` exercises real `AuthManager` and repository behavior.
- Do not call real external AI, OCR, email, Google, or Hugging Face endpoints from configured pytest tests; keep those isolated as in `tests/parity/test_data_async_parity.py` and `tests/test_auth_integration.py`.

## Fixtures and Factories

**Test Data:**
```python
# Pattern from `tests/conftest.py`
@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    from core.config import Config
    from core.db.connection import Database

    monkeypatch.setattr(Config, "DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(Config, "USE_POSTGRES", False)
    return Database()
```

```python
# Pattern from `tests/services/conftest.py`
@pytest.fixture
def tx_payload():
    return {
        "items": [
            {"product_id": 1, "quantity": 2, "unit_price": 10.0}
        ]
    }
```

**Location:**
- Use `tests/conftest.py` for app-wide fixtures: `app`, `client`, and `sqlite_db`.
- Use `tests/services/conftest.py` for shared service schemas and payloads: `db_stub`, `workflow_payload`, and `tx_payload`.
- Keep one-off data builders beside the tests that need them, as in `_make_excel()` in `tests/services/test_product_import.py`, `_create_test_schema()` in `tests/integration/test_catalog_crud_smoke.py`, and `_seed_product()` in `tests/test_inventory.py`.
- Use `tmp_path` for temporary database files in Flask client integration tests, as in `tests/integration/test_catalog_crud_smoke.py`.
- Use in-memory SQLite (`sqlite3.connect(":memory:")`) for pure service/repository tests, as in `tests/test_workflow_crud.py`, `tests/test_inventory.py`, and `tests/services/test_inventory_tx_service.py`.

## Coverage

**Requirements:** A backend coverage configuration exists in `.coveragerc`; a 20 percent gate is documented by `.planning/phases/14-backend-branch-integration-checkpoint/14-backend-coverage-report.md`. No executable gate script is detected under `scripts/`.

**Scope:**
- `.coveragerc` enables branch coverage with `branch = True`.
- `.coveragerc` measures `app`, `core`, and `routes`.
- `.coveragerc` omits `tests/*`, `*/__init__.py`, `dl_service/*`, `ai_agent_service/*`, `ui/*`, `static/*`, and `.planning/*`.
- `requirements-dev.txt` includes `pytest-cov>=5.0.0`.
- `.planning/phases/14-backend-branch-integration-checkpoint/14-backend-coverage-report.md` records a backend services/contracts coverage run using `--cov-fail-under=20.0`.

**View Coverage:**
```bash
python -m pytest tests/services tests/contracts -q --cov=app --cov=core --cov=routes --cov-config=.coveragerc --cov-report=term-missing:skip-covered
```

**Enforce Coverage:**
```bash
python -m pytest tests/services tests/contracts -q --cov=app --cov=core --cov=routes --cov-config=.coveragerc --cov-report=term-missing:skip-covered --cov-fail-under=20
```

## Test Types

**Unit Tests:**
- Service unit tests live in `tests/services/`, including `tests/services/test_workflow_service.py`, `tests/services/test_ai_chat_service.py`, `tests/services/test_inventory_tx_service.py`, and `tests/services/test_product_import.py`.
- Unit tests call service functions directly and use in-memory SQLite or local stubs, as in `tests/services/test_inventory_tx_service.py` and `tests/services/test_product_import.py`.
- Unit tests assert domain exceptions with `pytest.raises`, as in `tests/services/test_ai_chat_service.py`, `tests/services/test_inventory_tx_service.py`, and `tests/services/test_product_import.py`.

**Integration Tests:**
- Repository/service integration tests live in root `tests/test_*.py`, as in `tests/test_auth_integration.py`, `tests/test_inventory.py`, and `tests/test_workflow_crud.py`.
- Flask client integration smoke tests live under `tests/integration/`, as in `tests/integration/test_catalog_crud_smoke.py`.
- Integration tests use temporary SQLite databases and authenticated sessions instead of real external services, as in `tests/integration/test_catalog_crud_smoke.py`.

**Contract Tests:**
- Endpoint manifest and route registry checks live under `tests/contracts/`, using `.planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json` in `tests/contracts/test_contract_routes.py`.
- Smoke status checks use `.planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json` and Flask `client.open(...)` in `tests/contracts/test_contract_smoke.py`.

**Parity Tests:**
- Middleware parity tests live in `tests/parity/test_endpoint_middleware_parity.py` and assert unauthorized API JSON responses, page redirects, CSRF behavior, and rate-limit profile.
- Data/async parity tests live in `tests/parity/test_data_async_parity.py` and assert SQLite/PostgreSQL write paths plus background AI job status transitions with mocked dependencies.

**E2E Tests:**
- Not used: no Playwright, Selenium, Cypress, or browser E2E config is detected in `package.json`, `requirements-dev.txt`, or `tests/`.

**Frontend Tests:**
- Not used: static JavaScript files under `static/js/` have no configured test runner in `package.json`, and no JS test files are detected under `tests/`.

**DL/OCR Manual Scripts:**
- `dl_service/test_vietocr.py`, `dl_service/test_vietocr2.py`, `dl_service/test_ocr_pipeline.py`, and `debug/test_login.py` are outside `pytest.ini` discovery and should not be used as merge gates without moving or wrapping them under `tests/`.

## Common Patterns

**Async Testing:**
```python
# Pattern from `tests/parity/test_data_async_parity.py`
def test_background_ai_task_completed_parity(monkeypatch):
    statuses = []

    def _fake_save(job_id, payload):
        statuses.append(payload.get("status"))

    monkeypatch.setattr(ai_routes, "save_job_file", _fake_save)
    monkeypatch.setattr(ai_routes.requests, "post", _fake_post)

    ai_routes.background_ai_task("job-ok", 1, "hello")

    assert statuses[0] == "processing"
    assert statuses[-1] == "completed"
```

**Error Testing:**
```python
# Pattern from `tests/services/test_inventory_tx_service.py`
with pytest.raises(ServiceValidationError):
    inventory_tx_service.create_export_transaction(
        conn,
        user_id=12,
        payload={"items": [{"product_id": 1, "quantity": 5, "unit_price": 3.0}]},
        automation_engine=None,
    )
```

**Route Testing:**
```python
# Pattern from `tests/integration/test_catalog_crud_smoke.py`
response = client.post('/api/products', json=payload)

assert response.status_code == 200
payload_json = response.get_json()
assert payload_json['success'] is True
```

**Contract Testing:**
```python
# Pattern from `tests/contracts/test_contract_routes.py`
route_map = _route_method_map(app)
for entry in manifest["endpoints"]:
    path = entry["path"]
    expected_methods = set(entry.get("methods", []))
    assert path in route_map
    assert expected_methods.issubset(route_map[path])
```

**Parameterized Testing:**
```python
# Pattern from `tests/parity/test_endpoint_middleware_parity.py`
@pytest.mark.parametrize(
    "path",
    ["/api/workflows", "/api/imports", "/api/ai/history"],
)
def test_unauthorized_api_returns_json_401(parity_client, path):
    response = parity_client.get(path)
    assert response.status_code == 401
```

**Database State Testing:**
```python
# Pattern from `tests/test_inventory.py`
conn = _make_conn()
pid = _seed_product(conn, "Rice", stock=5)
result = inv.create_import_transaction(conn, user_id=1, payload={...})
stock = conn.execute(
    "SELECT stock_quantity FROM products WHERE id = ?",
    (pid,),
).fetchone()["stock_quantity"]
assert stock == 15
```

---

*Testing analysis: 2026-06-08*
