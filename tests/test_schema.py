"""Phase 2 schema tests.

Exercises Phase 2's new tables (suppliers, material_batches, warehouses,
warehouse_locations, stock_ledger) directly via core.sanxuat_db.get_connection()
since no HTTP routes exist yet for this schema (those land in 02-02/02-03/02-04).
"""
from core.sanxuat_db import get_connection, now


def test_suppliers_and_material_batches_schema(app):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO suppliers (code, name, created_at) VALUES (?, ?, ?)",
            ('NCC-TEST', 'Test Supplier', now()),
        )
        supplier_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO material_batches
                (code, material_code, material_name, unit, supplier_id, quantity, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ('LO-TEST', 'NVL-001', 'Vai cotton', 'm', supplier_id, 10, now()),
        )
        conn.commit()

        batch_row = conn.execute(
            "SELECT qc_status, is_deleted FROM material_batches WHERE code = ?",
            ('LO-TEST',),
        ).fetchone()
        assert batch_row['qc_status'] == 'pending'
        assert not batch_row['is_deleted']

        supplier_row = conn.execute(
            "SELECT is_deleted FROM suppliers WHERE code = ?",
            ('NCC-TEST',),
        ).fetchone()
        assert not supplier_row['is_deleted']
    finally:
        conn.close()


def test_warehouses_locations_and_ledger_schema(app):
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO warehouses (code, name) VALUES (?, ?)",
            ('KHO-TEST', 'Test Warehouse'),
        )
        warehouse_id = cur.lastrowid

        cur = conn.execute(
            "INSERT INTO warehouse_locations (warehouse_id, code, name) VALUES (?, ?, ?)",
            (warehouse_id, 'A1', 'Test Location'),
        )
        location_id = cur.lastrowid

        conn.execute(
            """
            INSERT INTO stock_ledger
                (entry_type, warehouse_id, location_id, product_code, product_name, unit, quantity_delta, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ('adjustment', warehouse_id, location_id, 'SP-TEST', 'Test Product', 'cái', 5, now()),
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT COALESCE(SUM(quantity_delta), 0) AS qty
            FROM stock_ledger
            WHERE warehouse_id = ? AND location_id = ? AND product_code = ?
            """,
            (warehouse_id, location_id, 'SP-TEST'),
        ).fetchone()
        assert row['qty'] == 5
    finally:
        conn.close()


def test_qc_results_schema(app):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO qc_results (batch_id, qc_status, created_at) VALUES (?, ?, ?)",
            (1, 'pending', now()),
        )
        conn.commit()

        row = conn.execute(
            "SELECT qc_note FROM qc_results WHERE batch_id = 1",
        ).fetchone()
        assert row['qc_note'] == ''

        conn.execute(
            "INSERT INTO qc_results (batch_id, qc_status, created_at) VALUES (?, ?, ?)",
            (1, 'passed', now()),
        )
        conn.commit()

        count_row = conn.execute(
            "SELECT COUNT(*) AS c FROM qc_results WHERE batch_id = 1",
        ).fetchone()
        assert count_row['c'] == 2
    finally:
        conn.close()


def test_material_batch_events_schema(app):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO material_batch_events (batch_id, event, created_at) VALUES (?, ?, ?)",
            (1, 'Bắt đầu sản xuất', now()),
        )
        conn.commit()

        row = conn.execute(
            "SELECT note FROM material_batch_events WHERE batch_id = 1",
        ).fetchone()
        assert row['note'] is None

        conn.execute(
            "INSERT INTO material_batch_events (batch_id, event, note, created_at) VALUES (?, ?, ?, ?)",
            (1, 'Kiểm tra đột xuất', 'Sự kiện ngoài danh mục mẫu', now()),
        )
        conn.commit()

        rows = conn.execute(
            "SELECT event FROM material_batch_events WHERE batch_id = 1 ORDER BY created_at ASC",
        ).fetchall()
        assert len(rows) == 2
        assert rows[0]['event'] == 'Bắt đầu sản xuất'
        assert rows[1]['event'] == 'Kiểm tra đột xuất'
    finally:
        conn.close()
