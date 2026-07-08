# Testing Patterns

**Analysis Date:** 2026-07-08

## Test Framework

**Runner:**
- `pytest>=8.0.0` (see `requirements-dev.txt`)
- Config: `pytest.ini`
  ```ini
  [pytest]
  testpaths = tests
  python_files = test_*.py
  pythonpath = .
  addopts = -q
  ```
  `pythonpath = .` allows absolute imports from repo root in tests without needing `sys.path` hacks.

**Supporting libraries** (`requirements-dev.txt`):
- `pytest-cov>=5.0.0` — coverage reporting
- `pytest-mock>=3.14.0` — `mocker` fixture for mocking
- `pytest-timeout>=2.3.1` — per-test timeouts
- `requests-mock>=1.12.1` — HTTP mocking for outbound integration calls (Google, Make.com, DL service)
- `ruff>=0.4.0` — lint (also used as a de facto style gate)

**Run Commands:**
```bash
pytest                          # run all tests (testpaths = tests)
pytest -q                       # quiet mode (default via addopts)
pytest tests/services/          # run one subdirectory
pytest tests/test_workflow_crud.py::test_create_and_get_scenario   # single test
pytest --cov=core --cov=routes  # coverage (pytest-cov installed, no default addopts cov flag)
```
There is also a standalone DL service test: `dl_service/test/test_ood_detection.py` — run separately with `pytest dl_service/test/` or as documented in `CLAUDE.md` for the DL service.

## Test File Organization

**Location:** All primary tests live under `tests/`, separate from source (not co-located). Subdirectories group tests by concern:
- `tests/` (root) — top-level cross-cutting suites: `test_auth_integration.py`, `test_automation_smoke.py`, `test_code_hygiene.py`, `test_dl_service_contracts.py`, `test_inventory.py`, `test_ops_subscription.py`, `test_security_hardening.py`, `test_services_extra.py`, `test_workflow_crud.py`
- `tests/services/` — service-layer unit tests, one file per service (`test_ai_chat_service.py`, `test_extraction_contracts.py`, `test_inventory_route_delegation.py`, `test_inventory_tx_service.py`, `test_product_import.py`, `test_workflow_service.py`) plus its own `conftest.py`
- `tests/contracts/` — contract/smoke tests validating route ↔ service handshake shape (`test_contract_routes.py`, `test_contract_smoke.py`)
- `tests/integration/` — cross-module integration (`test_catalog_crud_smoke.py`)
- `tests/parity/` — regression-style parity checks (`test_data_async_parity.py`, `test_endpoint_middleware_parity.py`)
- `tests/security/` — security tooling docs/config (README, model list, `strix` scanner config) rather than pytest files
- `tests/jobs/` — currently empty (reserved for background-job tests)

**Naming:** `test_*.py` files (enforced by `pytest.ini` `python_files = test_*.py`); individual test functions named `test_<behavior_under_test>`, e.g. `test_sale_delete_requires_owner`, `test_create_and_get_scenario`, `test_get_scenario_wrong_user_returns_none`.

## Test Structure

**Suite organization** — flat function-based tests (no class-based `TestX` suites observed); grouped visually with comment-banner section headers, e.g. `tests/test_workflow_crud.py`:
```python
# ── fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture()
def conn():
    ...

# ── WorkflowRepo direct ───────────────────────────────────────────────────────
def test_create_and_get_scenario(repo):
    sid = repo.create_scenario(1, "My Flow", "desc", True, '{"nodes":[]}')
    result = repo.get_scenario(sid, 1)
    assert result is not None
    assert result["name"] == "My Flow"
```

**Patterns:**
- Arrange/Act/Assert inline in a single small function, no separate setup/teardown methods.
- Fixtures scoped per-test (`@pytest.fixture()`) unless deliberately shared at session scope (`app` fixture in `tests/conftest.py` is `scope="session"`).
- Ownership/authorization tests assert a specific exception type is raised AND that no unintended side effect occurred, e.g. `tests/test_security_hardening.py::test_sale_delete_requires_owner`:
  ```python
  with pytest.raises(LookupError):
      delete_sale(conn, sale_id, user_id=1)

  cursor.execute("SELECT COUNT(*) AS count FROM sales WHERE id = ?", (sale_id,))
  assert cursor.fetchone()["count"] == 1
  ```

## Mocking

**Framework:** `pytest-mock` (`mocker` fixture) and stdlib `unittest.mock`/`monkeypatch` (pytest builtin) — used interchangeably depending on the test.

**Patterns:**
- `monkeypatch.setattr` for patching module-level attributes/config, e.g. `tests/test_code_hygiene.py`:
  ```python
  monkeypatch.setattr(Config, "GA_PROPERTY_ID", "123456789")
  monkeypatch.setattr(google_integration, "get_google_service", lambda *_args, **_kwargs: _Service())
  ```
- Hand-rolled fake objects for external SDK surfaces instead of `unittest.mock.MagicMock` when a specific call shape matters, e.g. the `_Files`/`_Service` fake Google Drive client in `tests/test_code_hygiene.py:30-42`.
- `monkeypatch.setattr(Config, "DATABASE_PATH", ...)` + `monkeypatch.setattr(Config, "USE_POSTGRES", False)` to redirect the app's real `Database` class at a temp SQLite file rather than mocking the DB layer itself — see the `sqlite_db` fixture in `tests/conftest.py`.

**What to mock:**
- External network/service boundaries: Google APIs (`core/google_integration.py`), Make.com webhooks (`core/make_integration.py`), DL service HTTP calls (`core/services/dl_client.py`) — use `requests-mock` or hand-rolled fakes.
- Config values that would otherwise require real credentials/environment (`Config.GA_PROPERTY_ID`, `Config.DATABASE_PATH`).

**What NOT to mock:**
- The database layer itself for service-layer tests — prefer real in-memory (`sqlite3.connect(":memory:")`) or temp-file SQLite (`sqlite_db` fixture) so tests exercise actual SQL and real row-shape behavior. `tests/services/conftest.py` explicitly documents this: the `db_stub` fixture docstring notes it "replaces the old `_StubRow` stub" and "returns actual database behaviour so contract smoke-tests exercise real service code paths instead of short-circuiting through a fake cursor."

## Fixtures and Factories

**Session-level app fixture** (`tests/conftest.py`):
```python
@pytest.fixture(scope="session")
def app():
    flask_app = getattr(app_module, "app", None)
    if flask_app is None:
        flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, RATELIMIT_ENABLED=False)
    return flask_app

@pytest.fixture()
def client(app):
    return app.test_client()
```
Sets `USE_POSTGRES=False` and `OAUTHLIB_INSECURE_TRANSPORT=1` env vars at module import time before the Flask app is imported, ensuring tests never touch Postgres or require OAuth HTTPS.

**Real-DB fixture** (`tests/conftest.py`):
```python
@pytest.fixture()
def sqlite_db(tmp_path, monkeypatch):
    from core.config import Config
    from core.db.connection import Database
    monkeypatch.setattr(Config, "DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(Config, "USE_POSTGRES", False)
    return Database()
```
Full schema is created via the app's real `init_database()` path against a fresh temp file per test — not a hand-maintained mini-schema.

**In-memory schema fixture** (`tests/services/conftest.py`): a hand-written `_SCHEMA_SQL` string creates only the tables needed by service-layer tests (`products`, `import_transactions`, `import_details`, `export_transactions`, `export_details`, `workflows`, `ai_chat_history`, `chat_sessions`, `chat_attachments`) against `sqlite3.connect(":memory:")`, seeded with one baseline product row. Shared fixtures: `db_stub`, `workflow_payload`, `tx_payload`.

**Location:** Fixtures live in `conftest.py` files at the level where they're shared: `tests/conftest.py` (app/client/sqlite_db — global), `tests/services/conftest.py` (service-layer schema/payload fixtures). Test-local fixtures are defined directly in the test file when only used there (e.g. `conn`/`repo` in `tests/test_workflow_crud.py`).

## Coverage

**Requirements:** No enforced coverage threshold detected — `pytest-cov` is installed but `pytest.ini` `addopts` does not include `--cov` or `--cov-fail-under`. Coverage is opt-in per invocation.

**View Coverage:**
```bash
pytest --cov=core --cov=routes --cov-report=term-missing
```

## Test Types

**Unit Tests:** Service-layer logic tested directly against in-memory SQLite without going through Flask routes — `tests/services/*`, most of `tests/test_workflow_crud.py`.

**Integration Tests:** Route ↔ service ↔ DB flows exercised via Flask `test_client()` and/or real repo classes against a schema — `tests/contracts/`, `tests/integration/`, `tests/test_auth_integration.py`, `tests/test_ops_subscription.py`.

**Security/Hardening Tests:** Ownership-scoping and cross-user access-control regression tests — `tests/test_security_hardening.py` (validates fixes described in `.planning/` history, e.g. "v1.2 security ownership hardening"). New security-sensitive service functions should get a matching `test_<action>_requires_owner`-style test here.

**Parity Tests:** `tests/parity/` guards that sync/async or middleware code paths behave identically — useful when a feature has two implementations that must stay in sync.

**Code Hygiene Tests:** `tests/test_code_hygiene.py` — assertions on source code itself (`inspect.getsource`) enforcing style rules like "no `print()`" and "no raw tuple indexing into rows." Add a new hygiene test here when introducing a new repo-wide style rule that should be automatically enforced.

**E2E Tests:** Not used — no Selenium/Playwright/Cypress test suite detected in `tests/`. `tests/security/strix` relates to a security scanning tool config, not browser E2E.

**DL Service Tests:** Separate from the main pytest suite — `dl_service/test/test_ood_detection.py`, run via the DL service's own workflow per `CLAUDE.md` (`python run_dl_service.py` / `python dl_service/model_app.py`).

## Common Patterns

**Ownership/authorization assertion:**
```python
with pytest.raises(LookupError):
    delete_sale(conn, sale_id, user_id=1)
```

**Source-inspection style assertion:**
```python
source = inspect.getsource(__import__("core.services.analytics_service", fromlist=[""]))
assert "print(" not in source
```

**Real-connection fixture + manual cleanup:**
```python
def test_sale_delete_requires_owner(sqlite_db):
    conn = sqlite_db.get_connection()
    try:
        ...
    finally:
        conn.close()
```

---

*Testing analysis: 2026-07-08*
