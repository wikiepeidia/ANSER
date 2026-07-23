import io
import json
import socket

import pytest

from core.auth import AuthManager
from core.automation_engine import AutomationEngine
from core.make_integration import trigger_webhook
from core.security import validate_upload
from core.services.customer_service import (
    delete_customer,
    get_all_customers,
    update_customer,
)
from core.services.product_service import (
    delete_product,
    get_all_products,
    update_product,
)
from core.services.sales_service import delete_sale


class _Upload:
    def __init__(self, filename, mimetype, data=b"data"):
        self.filename = filename
        self.mimetype = mimetype
        self.stream = io.BytesIO(data)
        self.content_length = len(data)


def test_sale_delete_requires_owner(sqlite_db):
    conn = sqlite_db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sales (user_id, total_amount) VALUES (?, ?)", (2, 120))
        sale_id = cursor.lastrowid
        conn.commit()

        with pytest.raises(LookupError):
            delete_sale(conn, sale_id, user_id=1)

        cursor.execute("SELECT COUNT(*) AS count FROM sales WHERE id = ?", (sale_id,))
        assert cursor.fetchone()["count"] == 1
    finally:
        conn.close()


def test_product_customer_owner_scope(sqlite_db):
    conn = sqlite_db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (code, name, created_by) VALUES (?, ?, ?)",
            ("P-OWNER", "Owner Product", 2),
        )
        product_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO customers (code, name, created_by) VALUES (?, ?, ?)",
            ("C-OWNER", "Owner Customer", 2),
        )
        customer_id = cursor.lastrowid
        conn.commit()

        assert get_all_products(conn, user_id=1, role="manager") == []
        assert len(get_all_products(conn, user_id=1, role="admin")) == 1
        assert get_all_customers(conn, user_id=1, role="manager") == []
        assert len(get_all_customers(conn, user_id=1, role="admin")) == 1

        with pytest.raises(LookupError):
            update_product(conn, product_id, "Nope", "", "pcs", 0, 0, "", user_id=1, role="manager")
        with pytest.raises(LookupError):
            delete_product(conn, product_id, user_id=1, role="manager")
        with pytest.raises(LookupError):
            update_customer(conn, customer_id, "Nope", "", "", "", "", user_id=1, role="manager")
        with pytest.raises(LookupError):
            delete_customer(conn, customer_id, user_id=1, role="manager")
    finally:
        conn.close()


def test_operations_reports_and_automations_are_owner_scoped(sqlite_db, monkeypatch):
    import core.services.operations_service as operations_service

    monkeypatch.setattr(operations_service, "db_manager", sqlite_db)
    conn = sqlite_db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO export_transactions (total_amount, created_by) VALUES (?, ?)", (100, 1))
        cursor.execute("INSERT INTO export_transactions (total_amount, created_by) VALUES (?, ?)", (900, 2))
        cursor.execute("INSERT INTO import_transactions (total_amount, created_by) VALUES (?, ?)", (40, 1))
        cursor.execute("INSERT INTO import_transactions (total_amount, created_by) VALUES (?, ?)", (300, 2))
        report_id = "report-mine"
        cursor.execute(
            "INSERT INTO scheduled_reports (id, name, report_type, frequency, channel, recipients, created_by, last_sent_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (report_id, "Mine", "sales", "daily", "email", "a@test.com", 1),
        )
        other_report_id = "report-other"
        cursor.execute(
            "INSERT INTO scheduled_reports (id, name, report_type, frequency, channel, recipients, created_by)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (other_report_id, "Other", "sales", "daily", "email", "b@test.com", 2),
        )
        cursor.execute(
            "INSERT INTO se_automations (name, type, config, enabled, created_by) VALUES (?, ?, ?, ?, ?)",
            ("Mine", "low_stock", "{}", 1, 1),
        )
        cursor.execute(
            "INSERT INTO se_automations (name, type, config, enabled, created_by) VALUES (?, ?, ?, ?, ?)",
            ("Other", "low_stock", "{}", 1, 2),
        )
        conn.commit()

        stats = operations_service.get_report_stats(user_id=1, role="manager")
        assert stats["revenue"] == 100
        assert stats["expense"] == 40
        assert len(operations_service.get_scheduled_reports(user_id=1, role="manager")) == 1
        assert len(operations_service.get_automations(user_id=1, role="manager")) == 1

        with pytest.raises(LookupError):
            operations_service.delete_scheduled_report(other_report_id, user_id=1, role="manager")
        operations_service.delete_scheduled_report(report_id, user_id=1, role="manager")
    finally:
        conn.close()


def test_automation_import_uses_rule_owner_and_rejects_other_owner_product(sqlite_db):
    conn = sqlite_db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (code, name, price, stock_quantity, created_by) VALUES (?, ?, ?, ?, ?)",
            ("P1", "Mine", 10, 3, 1),
        )
        mine_product_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO products (code, name, price, stock_quantity, created_by) VALUES (?, ?, ?, ?, ?)",
            ("P2", "Other", 10, 3, 2),
        )
        other_product_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO se_automations (name, type, config, enabled, created_by) VALUES (?, ?, ?, ?, ?)",
            ("Mine Rule", "low_stock", json.dumps({"reorder_quantity": 5}), 1, 1),
        )
        auto_id = cursor.lastrowid
        conn.commit()

        engine = AutomationEngine(sqlite_db)
        engine.execute_import_automation(auto_id, {"reorder_quantity": 5}, other_product_id)
        cursor.execute("SELECT COUNT(*) AS count FROM import_transactions")
        assert cursor.fetchone()["count"] == 0

        engine.execute_import_automation(auto_id, {"reorder_quantity": 5}, mine_product_id)
        cursor.execute("SELECT created_by FROM import_transactions")
        assert cursor.fetchone()["created_by"] == 1
    finally:
        conn.close()


def test_google_user_repo_uses_bcrypt_hash(sqlite_db):
    raw_password = "temporary-google-password"
    hashed = AuthManager.hash_password(raw_password)

    result = sqlite_db.upsert_google_user(
        "google@example.com",
        "Google User",
        "https://example.com/avatar.png",
        "{}",
        hashed,
    )

    conn = sqlite_db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE id = ?", (result["id"],))
        stored = cursor.fetchone()["password"]
        assert stored.startswith("$2")
        assert AuthManager.verify_password(raw_password, stored)
    finally:
        conn.close()


def test_webhook_blocks_private_dns_before_request(monkeypatch):
    monkeypatch.setattr(
        "core.security.socket.getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )

    def fail_request(*args, **kwargs):
        raise AssertionError("request should not be sent")

    monkeypatch.setattr("core.make_integration.requests.post", fail_request)

    result = trigger_webhook("http://example.test/hook", payload={"ok": True})

    assert result["status"] == "error"
    assert "not allowed" in result["message"]


def test_upload_validation_rejects_unsupported_type():
    upload = _Upload("payload.exe", "application/x-msdownload")

    with pytest.raises(ValueError, match="Unsupported file type"):
        validate_upload(upload, {"png"}, {"image/png"}, max_bytes=1024)
