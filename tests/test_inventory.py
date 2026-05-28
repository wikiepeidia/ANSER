"""Integration tests for inventory, sales, and activity repos using SQLite in-memory."""
import sqlite3

import pytest

import core.services.inventory_tx_service as inv
import core.services.sales_service as sales
from core.db.activity_repo import ActivityRepo
from core.db.chat_repo import ChatRepo
from core.services.service_errors import ServiceValidationError


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            price REAL DEFAULT 0,
            stock_quantity INTEGER DEFAULT 0,
            created_by INTEGER
        );
        CREATE TABLE import_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            supplier_name TEXT,
            total_amount REAL DEFAULT 0,
            notes TEXT,
            status TEXT DEFAULT 'completed',
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE import_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            product_id INTEGER,
            quantity REAL DEFAULT 0,
            unit_price REAL DEFAULT 0,
            total_price REAL DEFAULT 0
        );
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT
        );
        CREATE TABLE export_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            customer_id INTEGER,
            total_amount REAL DEFAULT 0,
            notes TEXT,
            status TEXT DEFAULT 'completed',
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE export_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            export_id INTEGER NOT NULL,
            product_id INTEGER,
            quantity REAL DEFAULT 0,
            unit_price REAL DEFAULT 0,
            total_price REAL DEFAULT 0
        );
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total_amount REAL,
            amount_given REAL,
            change_amount REAL,
            items TEXT,
            payment_method TEXT DEFAULT 'cash',
            workspace_id INTEGER,
            category TEXT DEFAULT 'Retail',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            ip_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE ai_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            workspace_id INTEGER,
            title TEXT,
            last_active TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE chat_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            file_name TEXT,
            file_type TEXT,
            analysis_summary TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    return conn


def _seed_product(conn, name="Rice", stock=10, price=5.0):
    conn.execute(
        "INSERT INTO products (code, name, price, stock_quantity, created_by)"
        " VALUES (?, ?, ?, ?, 1)",
        (f"P-{name}", name, price, stock),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM products WHERE name = ?", (name,)).fetchone()
    return row["id"]


# ── import transaction ────────────────────────────────────────────────────────

def test_import_increments_existing_product_stock():
    conn = _make_conn()
    pid = _seed_product(conn, "Rice", stock=5)
    result = inv.create_import_transaction(
        conn, user_id=1,
        payload={"supplier_name": "ACME", "items": [{"product_id": pid, "quantity": 10, "unit_price": 4.0}]},
    )
    assert result["message"] == "Import created successfully"
    stock = conn.execute("SELECT stock_quantity FROM products WHERE id = ?", (pid,)).fetchone()["stock_quantity"]
    assert stock == 15


def test_import_creates_new_product_by_name():
    conn = _make_conn()
    result = inv.create_import_transaction(
        conn, user_id=1,
        payload={"items": [{"product_name": "NewProduct", "quantity": 3, "unit_price": 2.0}]},
    )
    assert result["message"] == "Import created successfully"
    row = conn.execute("SELECT stock_quantity FROM products WHERE name = 'NewProduct'").fetchone()
    assert row["stock_quantity"] == 3


def test_import_total_amount_is_calculated():
    conn = _make_conn()
    pid = _seed_product(conn, "Milk", stock=0, price=5.0)
    result = inv.create_import_transaction(
        conn, user_id=1,
        payload={"items": [{"product_id": pid, "quantity": 4, "unit_price": 2.5}]},
    )
    row = conn.execute("SELECT total_amount FROM import_transactions WHERE id = ?", (result["id"],)).fetchone()
    assert row["total_amount"] == pytest.approx(10.0)


def test_import_no_items_raises():
    conn = _make_conn()
    with pytest.raises(ServiceValidationError):
        inv.create_import_transaction(conn, user_id=1, payload={"items": []})


# ── get import details ────────────────────────────────────────────────────────

def test_get_import_details_returns_transaction_and_items():
    conn = _make_conn()
    pid = _seed_product(conn, "Coffee", stock=0)
    result = inv.create_import_transaction(
        conn, user_id=1,
        payload={"supplier_name": "SupplierX", "items": [{"product_id": pid, "quantity": 5, "unit_price": 3.0}]},
    )
    details = inv.get_import_transaction_details(conn, result["id"])
    assert details is not None
    assert details["transaction"]["supplier_name"] == "SupplierX"
    assert len(details["details"]) == 1
    assert details["details"][0]["quantity"] == 5
    assert details["details"][0]["product_name"] == "Coffee"


def test_get_import_details_not_found_returns_none():
    conn = _make_conn()
    assert inv.get_import_transaction_details(conn, 9999) is None


# ── export transaction ────────────────────────────────────────────────────────

def test_export_decrements_stock():
    conn = _make_conn()
    pid = _seed_product(conn, "Beans", stock=20)
    result = inv.create_export_transaction(
        conn, user_id=1,
        payload={"items": [{"product_id": pid, "quantity": 7, "unit_price": 3.0}]},
    )
    assert result["message"] == "Export created successfully"
    stock = conn.execute("SELECT stock_quantity FROM products WHERE id = ?", (pid,)).fetchone()["stock_quantity"]
    assert stock == 13


def test_export_insufficient_stock_raises_and_rolls_back():
    conn = _make_conn()
    pid = _seed_product(conn, "Tea", stock=2)
    with pytest.raises(ServiceValidationError):
        inv.create_export_transaction(
            conn, user_id=1,
            payload={"items": [{"product_id": pid, "quantity": 5, "unit_price": 1.0}]},
        )
    # Stock unchanged after rollback
    stock = conn.execute("SELECT stock_quantity FROM products WHERE id = ?", (pid,)).fetchone()["stock_quantity"]
    assert stock == 2
    assert conn.execute("SELECT COUNT(*) AS cnt FROM export_transactions").fetchone()["cnt"] == 0


def test_export_unknown_product_raises():
    conn = _make_conn()
    with pytest.raises(ServiceValidationError):
        inv.create_export_transaction(
            conn, user_id=1,
            payload={"items": [{"product_id": 9999, "quantity": 1, "unit_price": 1.0}]},
        )


# ── get export details ────────────────────────────────────────────────────────

def test_get_export_details_returns_transaction_and_items():
    conn = _make_conn()
    pid = _seed_product(conn, "Sugar", stock=50)
    result = inv.create_export_transaction(
        conn, user_id=1,
        payload={"notes": "bulk order", "items": [{"product_id": pid, "quantity": 10, "unit_price": 2.0}]},
    )
    details = inv.get_export_transaction_details(conn, result["id"])
    assert details is not None
    assert details["transaction"]["notes"] == "bulk order"
    assert details["transaction"]["customer_name"] == ""
    assert len(details["details"]) == 1
    assert details["details"][0]["quantity"] == 10


def test_get_export_details_not_found_returns_none():
    conn = _make_conn()
    assert inv.get_export_transaction_details(conn, 9999) is None


# ── sales_service ─────────────────────────────────────────────────────────────

def test_sales_create_and_list():
    conn = _make_conn()
    import json
    items = [{"name": "Coffee", "qty": 2, "price": 30000}]
    sales.create_sale(conn, user_id=1, total_amount=60000, amount_given=100000,
                      change_amount=40000, items=json.dumps(items),
                      payment_method="cash", workspace_id=1, category="Retail")
    history = sales.get_sales_history(conn, user_id=1)
    assert len(history) == 1
    assert history[0]["amount"] == 60000
    assert history[0]["item_count"] == 2


def test_sales_delete():
    conn = _make_conn()
    sales.create_sale(conn, user_id=1, total_amount=10000, amount_given=10000,
                      change_amount=0, items="[]", payment_method="cash",
                      workspace_id=1, category="Retail")
    history = sales.get_sales_history(conn, user_id=1)
    sale_id = history[0]["id"]
    sales.delete_sale(conn, sale_id)
    assert sales.get_sales_history(conn, user_id=1) == []


def test_sales_delete_nonexistent_raises():
    conn = _make_conn()
    with pytest.raises(LookupError):
        sales.delete_sale(conn, 9999)


def test_sales_search_by_payment_method():
    conn = _make_conn()
    sales.create_sale(conn, 1, 100, 100, 0, "[]", "card", 1, "Retail")
    sales.create_sale(conn, 1, 200, 200, 0, "[]", "cash", 1, "Retail")
    results = sales.get_sales_history(conn, user_id=1, search_query="card")
    assert len(results) == 1
    assert results[0]["payment_method"] == "card"


# ── ActivityRepo ──────────────────────────────────────────────────────────────

def test_activity_log_and_fetch():
    conn = _make_conn()
    repo = ActivityRepo(conn)
    repo.log_activity(user_id=1, action="login", details="ok", ip_address="127.0.0.1")
    repo.log_activity(user_id=1, action="logout")
    activities = repo.get_recent_activities(limit=10)
    assert len(activities) == 2
    actions = {a["action"] for a in activities}
    assert actions == {"login", "logout"}


def test_activity_recent_limit():
    conn = _make_conn()
    repo = ActivityRepo(conn)
    for i in range(5):
        repo.log_activity(user_id=1, action=f"action_{i}")
    assert len(repo.get_recent_activities(limit=3)) == 3


# ── ChatRepo ──────────────────────────────────────────────────────────────────

def test_chat_add_and_get_history():
    conn = _make_conn()
    repo = ChatRepo(conn)
    repo.add_ai_message(user_id=1, role="user", content="Hello")
    repo.add_ai_message(user_id=1, role="assistant", content="Hi there")
    history = repo.get_ai_history(user_id=1, limit=10)
    assert "User: Hello" in history
    assert "AI: Hi there" in history


def test_chat_history_limit():
    conn = _make_conn()
    repo = ChatRepo(conn)
    for i in range(10):
        repo.add_ai_message(1, "user", f"msg {i}")
    history = repo.get_ai_history(1, limit=3)
    # Returns last 3 messages formatted
    assert history.count("\n") == 2


def test_chat_save_attachment_creates_session():
    conn = _make_conn()
    repo = ChatRepo(conn)
    repo.save_attachment(user_id=1, workspace_id=1,
                         filename="invoice.pdf", filetype="application/pdf",
                         analysis="Total: 500k VND")
    row = conn.execute("SELECT COUNT(*) AS cnt FROM chat_sessions").fetchone()
    assert row["cnt"] == 1
    att = conn.execute("SELECT analysis_summary FROM chat_attachments").fetchone()
    assert att["analysis_summary"] == "Total: 500k VND"


def test_chat_second_attachment_reuses_session():
    conn = _make_conn()
    repo = ChatRepo(conn)
    repo.save_attachment(1, 1, "a.pdf", "application/pdf", "summary A")
    repo.save_attachment(1, 1, "b.pdf", "application/pdf", "summary B")
    sessions = conn.execute("SELECT COUNT(*) AS cnt FROM chat_sessions").fetchone()["cnt"]
    attachments = conn.execute("SELECT COUNT(*) AS cnt FROM chat_attachments").fetchone()["cnt"]
    assert sessions == 1   # same session reused
    assert attachments == 2
