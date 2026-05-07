"""Unit tests for inventory transaction service behavior."""

import sqlite3

import pytest

import core.services.inventory_tx_service as inventory_tx_service
from core.services.service_errors import ServiceValidationError


def _new_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            name TEXT,
            price REAL,
            stock_quantity INTEGER,
            created_by INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE import_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            supplier_name TEXT,
            total_amount REAL,
            notes TEXT,
            status TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE import_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price REAL,
            total_price REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE export_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            customer_id INTEGER,
            total_amount REAL,
            notes TEXT,
            status TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE export_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            export_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            unit_price REAL,
            total_price REAL
        )
        """
    )
    conn.commit()
    return conn


def test_create_import_transaction_calculates_total_and_increments_stock():
    conn = _new_conn()
    conn.execute(
        "INSERT INTO products (code, name, price, stock_quantity, created_by) VALUES (?, ?, ?, ?, ?)",
        ("P-1", "Rice", 10.0, 5, 1),
    )
    conn.commit()

    result = inventory_tx_service.create_import_transaction(
        conn,
        user_id=9,
        payload={
            "supplier_name": "ACME",
            "notes": "batch",
            "items": [{"product_id": 1, "quantity": 3, "unit_price": 4.5}],
        },
    )

    assert result["message"] == "Import created successfully"
    total_amount = conn.execute("SELECT total_amount FROM import_transactions WHERE id = ?", (result["id"],)).fetchone()[0]
    assert total_amount == pytest.approx(13.5)

    stock_quantity = conn.execute("SELECT stock_quantity FROM products WHERE id = 1").fetchone()[0]
    assert stock_quantity == 8


def test_create_export_transaction_decrements_stock():
    conn = _new_conn()
    conn.execute(
        "INSERT INTO products (code, name, price, stock_quantity, created_by) VALUES (?, ?, ?, ?, ?)",
        ("P-2", "Milk", 5.0, 10, 1),
    )
    conn.commit()

    class _AutomationStub:
        def __init__(self):
            self.calls = []

        def check_low_stock(self, product_id, stock_quantity):
            self.calls.append((product_id, stock_quantity))

    automation_stub = _AutomationStub()

    result = inventory_tx_service.create_export_transaction(
        conn,
        user_id=11,
        payload={
            "customer_id": None,
            "notes": "sale",
            "items": [{"product_id": 1, "quantity": 4, "unit_price": 5.0}],
        },
        automation_engine=automation_stub,
    )

    assert result["message"] == "Export created successfully"
    stock_quantity = conn.execute("SELECT stock_quantity FROM products WHERE id = 1").fetchone()[0]
    assert stock_quantity == 6
    assert automation_stub.calls == [(1, 6)]


def test_create_export_transaction_rolls_back_on_insufficient_stock():
    conn = _new_conn()
    conn.execute(
        "INSERT INTO products (code, name, price, stock_quantity, created_by) VALUES (?, ?, ?, ?, ?)",
        ("P-3", "Beans", 3.0, 1, 1),
    )
    conn.commit()

    with pytest.raises(ServiceValidationError):
        inventory_tx_service.create_export_transaction(
            conn,
            user_id=12,
            payload={
                "customer_id": None,
                "notes": "oversell",
                "items": [{"product_id": 1, "quantity": 5, "unit_price": 3.0}],
            },
            automation_engine=None,
        )

    tx_count = conn.execute("SELECT COUNT(*) FROM export_transactions").fetchone()[0]
    details_count = conn.execute("SELECT COUNT(*) FROM export_details").fetchone()[0]
    stock_quantity = conn.execute("SELECT stock_quantity FROM products WHERE id = 1").fetchone()[0]

    assert tx_count == 0
    assert details_count == 0
    assert stock_quantity == 1
