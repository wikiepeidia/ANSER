"""Route delegation checks for inventory service extraction."""

from types import SimpleNamespace

import app as app_module
import routes.inventory_routes as inventory_routes


class _ConnStub:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _DbManagerStub:
    def __init__(self, conn):
        self._conn = conn

    def get_connection(self):
        return self._conn


def _call_wrapped(route_fn, path, payload):
    wrapped = getattr(route_fn, "__wrapped__", route_fn)
    with app_module.app.test_request_context(path, method="POST", json=payload):
        return wrapped()


def test_api_create_import_delegates_to_inventory_service(monkeypatch):
    conn = _ConnStub()
    called = {}

    def _fake_create_import(db_conn, user_id, payload):
        called["db_conn"] = db_conn
        called["user_id"] = user_id
        called["payload"] = payload
        return {"message": "Import created successfully", "id": 101}

    monkeypatch.setattr(app_module, "current_user", SimpleNamespace(id=55))
    monkeypatch.setattr(app_module, "db_manager", _DbManagerStub(conn))
    monkeypatch.setattr(inventory_routes.inventory_tx_service, "create_import_transaction", _fake_create_import)

    response = _call_wrapped(
        inventory_routes.api_create_import,
        "/api/imports",
        {"items": [{"product_id": 1, "quantity": 2, "unit_price": 5}]},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["id"] == 101
    assert called["db_conn"] is conn
    assert called["user_id"] == 55
    assert conn.closed is True


def test_api_create_export_delegates_to_inventory_service(monkeypatch):
    conn = _ConnStub()
    called = {}

    class _AutomationStub:
        pass

    automation_stub = _AutomationStub()

    def _fake_create_export(db_conn, user_id, payload, automation_engine):
        called["db_conn"] = db_conn
        called["user_id"] = user_id
        called["payload"] = payload
        called["automation_engine"] = automation_engine
        return {"message": "Export created successfully", "id": 202}

    monkeypatch.setattr(app_module, "current_user", SimpleNamespace(id=56))
    monkeypatch.setattr(app_module, "db_manager", _DbManagerStub(conn))
    monkeypatch.setattr(app_module, "automation_engine", automation_stub)
    monkeypatch.setattr(inventory_routes.inventory_tx_service, "create_export_transaction", _fake_create_export)

    response = _call_wrapped(
        inventory_routes.api_create_export,
        "/api/exports",
        {"items": [{"product_id": 1, "quantity": 1, "unit_price": 9}]},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["id"] == 202
    assert called["db_conn"] is conn
    assert called["user_id"] == 56
    assert called["automation_engine"] is automation_stub
    assert conn.closed is True
