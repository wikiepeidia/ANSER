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
