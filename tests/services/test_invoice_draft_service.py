"""Behavioral tests for core.services.invoice_draft_service.create_invoice_draft().

Covers: status enforcement (never trusts client-supplied status), exact-name
product matching with no auto-create, raw_name preservation for unmatched
items, and the no-stock-mutation invariant (warehouse_stock/products.
stock_quantity untouched).
"""

import sqlite3

import pytest

import core.services.invoice_draft_service as draft_service
from core.services.service_errors import ServiceValidationError


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
            warehouse_id INTEGER,
            source TEXT,
            raw_ocr_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE import_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            product_id INTEGER,
            quantity REAL DEFAULT 0,
            unit_price REAL DEFAULT 0,
            total_price REAL DEFAULT 0,
            raw_name TEXT,
            is_reduced_vat INTEGER
        );
        CREATE TABLE warehouse_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            warehouse_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            UNIQUE(warehouse_id, product_id)
        );
    """)
    return conn


def _seed_product(conn, name, stock=10, price=1.0, code=None):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (code, name, price, stock_quantity) VALUES (?, ?, ?, ?)",
        (code, name, price, stock),
    )
    conn.commit()
    return cursor.lastrowid


def _clean_payload(**overrides):
    payload = {
        "success": True,
        "needs_manual_review": False,
        "invoice": {
            "items": [{"name": "Coca Cola", "price": 12000, "qty": 5, "is_reduced_vat": True}],
            "total": 60000,
        },
    }
    payload.update(overrides)
    return payload


# ── status enforcement ──────────────────────────────────────────────────────

def test_valid_payload_creates_pending_review_row_with_matched_item():
    conn = _make_conn()
    pid = _seed_product(conn, "Coca Cola", stock=20)

    result = draft_service.create_invoice_draft(conn, _clean_payload())

    assert result["status"] == "pending_review"
    assert result["matched_count"] == 1
    assert result["unmatched_count"] == 0

    tx = conn.execute(
        "SELECT status FROM import_transactions WHERE id = ?", (result["id"],)
    ).fetchone()
    assert tx["status"] == "pending_review"

    detail = conn.execute(
        "SELECT product_id, raw_name, is_reduced_vat FROM import_details WHERE import_id = ?",
        (result["id"],),
    ).fetchone()
    assert detail["product_id"] == pid
    assert detail["raw_name"] == "Coca Cola"
    assert detail["is_reduced_vat"] == 1


def test_client_supplied_status_field_is_ignored():
    conn = _make_conn()
    _seed_product(conn, "Coca Cola", stock=20)

    payload = _clean_payload(status="completed")
    result = draft_service.create_invoice_draft(conn, payload)

    tx = conn.execute(
        "SELECT status FROM import_transactions WHERE id = ?", (result["id"],)
    ).fetchone()
    assert tx["status"] == "pending_review"


# ── product matching — conservative, no auto-create ────────────────────────

def test_unmatched_item_gets_null_product_id_and_preserves_raw_name():
    conn = _make_conn()

    payload = _clean_payload(invoice={
        "items": [{"name": "Coco Colla", "price": 12000, "qty": 5, "is_reduced_vat": False}],
        "total": 60000,
    })
    result = draft_service.create_invoice_draft(conn, payload)

    assert result["matched_count"] == 0
    assert result["unmatched_count"] == 1

    detail = conn.execute(
        "SELECT product_id, raw_name FROM import_details WHERE import_id = ?",
        (result["id"],),
    ).fetchone()
    assert detail["product_id"] is None
    assert detail["raw_name"] == "Coco Colla"

    products_count = conn.execute("SELECT COUNT(*) AS cnt FROM products").fetchone()["cnt"]
    assert products_count == 0


# ── no stock mutation ───────────────────────────────────────────────────────

def test_no_stock_mutation_on_matched_item():
    conn = _make_conn()
    pid = _seed_product(conn, "Coca Cola", stock=20)
    conn.execute(
        "INSERT INTO warehouse_stock (warehouse_id, product_id, stock_quantity) VALUES (1, ?, 20)",
        (pid,),
    )
    conn.commit()

    before_ws_count = conn.execute("SELECT COUNT(*) AS cnt FROM warehouse_stock").fetchone()["cnt"]
    before_stock = conn.execute(
        "SELECT stock_quantity FROM products WHERE id = ?", (pid,)
    ).fetchone()["stock_quantity"]

    draft_service.create_invoice_draft(conn, _clean_payload())

    after_ws_count = conn.execute("SELECT COUNT(*) AS cnt FROM warehouse_stock").fetchone()["cnt"]
    after_stock = conn.execute(
        "SELECT stock_quantity FROM products WHERE id = ?", (pid,)
    ).fetchone()["stock_quantity"]

    assert after_ws_count == before_ws_count
    assert after_stock == before_stock


# ── validation ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("overrides", [
    {"success": False},
    {"needs_manual_review": True},
    {"invoice": {}},
    {"invoice": {"items": [], "total": 0}},
    {"invoice": {"items": [{"name": "X", "price": 1, "qty": 1}]}},  # missing total
])
def test_invalid_payload_raises_and_creates_nothing(overrides):
    conn = _make_conn()

    payload = _clean_payload(**overrides)
    with pytest.raises(ServiceValidationError):
        draft_service.create_invoice_draft(conn, payload)

    count = conn.execute("SELECT COUNT(*) AS cnt FROM import_transactions").fetchone()["cnt"]
    assert count == 0
