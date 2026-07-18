"""Basic insert/query tests for the production_orders table (core/sanxuat_db.py).

Runs against the isolated temp SQLite DB from the `app` fixture, not the
real Postgres/Neon sanxuat_business DB — see tests/conftest.py.
"""
from core.sanxuat_db import get_connection, now


def _insert_product(conn, code="SP-TEST-01"):
    conn.execute(
        'INSERT INTO products (code, name, created_at, updated_at) VALUES (?, ?, ?, ?)',
        (code, "Sản phẩm test", now(), now()),
    )
    conn.commit()
    return conn.execute('SELECT id FROM products WHERE code = ?', (code,)).fetchone()['id']


def test_create_and_fetch_production_order(app):
    conn = get_connection()
    try:
        product_id = _insert_product(conn, "SP-TEST-PO-1")

        conn.execute(
            'INSERT INTO production_orders '
            '(order_code, product_id, quantity, status, created_by, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            ("DH-TEST-001", product_id, 100, "approved", 1, now()),
        )
        conn.commit()

        row = conn.execute(
            'SELECT order_code, product_id, quantity, status, created_by, approved_by, '
            'started_at, finished_at FROM production_orders WHERE order_code = ?',
            ("DH-TEST-001",),
        ).fetchone()

        assert row is not None
        assert row['product_id'] == product_id
        assert row['quantity'] == 100
        assert row['status'] == "approved"
        assert row['created_by'] == 1
        assert row['approved_by'] is None
        assert row['started_at'] is None
        assert row['finished_at'] is None
    finally:
        conn.close()


def test_production_order_default_status(app):
    conn = get_connection()
    try:
        product_id = _insert_product(conn, "SP-TEST-PO-2")

        conn.execute(
            'INSERT INTO production_orders (order_code, product_id, quantity, created_at) '
            'VALUES (?, ?, ?, ?)',
            ("DH-TEST-002", product_id, 50, now()),
        )
        conn.commit()

        row = conn.execute(
            'SELECT status FROM production_orders WHERE order_code = ?',
            ("DH-TEST-002",),
        ).fetchone()

        assert row['status'] == "draft"
    finally:
        conn.close()


def test_production_order_code_must_be_unique(app):
    conn = get_connection()
    try:
        product_id = _insert_product(conn, "SP-TEST-PO-3")
        conn.execute(
            'INSERT INTO production_orders (order_code, product_id, quantity, created_at) '
            'VALUES (?, ?, ?, ?)',
            ("DH-TEST-003", product_id, 10, now()),
        )
        conn.commit()

        try:
            conn.execute(
                'INSERT INTO production_orders (order_code, product_id, quantity, created_at) '
                'VALUES (?, ?, ?, ?)',
                ("DH-TEST-003", product_id, 20, now()),
            )
            conn.commit()
            raised = False
        except Exception:
            raised = True

        assert raised
    finally:
        conn.close()
