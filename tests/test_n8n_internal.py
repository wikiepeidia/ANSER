"""Covers N8N-01: routes/n8n_api.py's internal_rag(action) per-action
dispatch to real domain tables (material_batches, production_orders +
production_order_events), instead of the generic automation_events sink.

Uses the module-scoped `client` fixture (no login) — internal_rag is called
by n8n, which carries no Flask-Login session (see tests/conftest.py).
"""
from core.sanxuat_db import get_connection


def test_material_batch_insert(client):
    resp = client.post('/api/n8n/internal/rag/material-batch-insert', json={
        'material_code': 'NVL-001',
        'qty_kg': 50,
        'farmer': 'Nông trại Test N8N',
        'lot_code': 'IGNORED-CODE',
        'harvest_ts': '2026-07-01',
        'unit_cost_vnd': 12000,
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['success'] is True
    assert body['code'].startswith('LO-')
    assert body['lot_code'] == body['code']
    assert body['farmer'] == 'Nông trại Test N8N'
    assert body['material_code'] == 'NVL-001'
    assert body['qty_kg'] == 50
    assert body['status'] == 'ok'

    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT created_by, supplier_id FROM material_batches WHERE id = ?',
            (body['id'],),
        ).fetchone()
    finally:
        conn.close()
    assert row['created_by'] is None
    assert row['supplier_id'] is not None

    resp2 = client.post('/api/n8n/internal/rag/material-batch-insert', json={
        'material_code': 'BOGUS-CODE',
        'qty_kg': 10,
    })
    assert resp2.status_code == 400
    assert resp2.get_json()['message'] == 'Mã nguyên vật liệu không hợp lệ'

    resp3 = client.post('/api/n8n/internal/rag/material-batch-insert', json={
        'material_code': 'NVL-001',
        'qty_kg': 0,
    })
    assert resp3.status_code == 400


def test_production_order_insert(client):
    resp = client.post('/api/n8n/internal/rag/production-order-insert', json={
        'product_code': 'SP-001',
        'product_name': 'Áo thun Test N8N',
        'qty_to_produce': 20,
        'customer_code': 'KH-N8N-01',
        'order_code': 'IGNORED',
        'qty_ordered': 25,
        'unit_price': 100000,
        'region': 'HN',
        'deadline': '2026-08-01',
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['success'] is True
    assert body['code'].startswith('DH-')
    assert body['status'] == 'ok'

    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT created_by, status, quantity, customer_name FROM production_orders '
            'WHERE id = ?',
            (body['id'],),
        ).fetchone()
        events = conn.execute(
            'SELECT event FROM production_order_events WHERE order_id = ?',
            (body['id'],),
        ).fetchall()
    finally:
        conn.close()
    assert row['created_by'] is None
    assert row['status'] == 'draft'
    assert row['quantity'] == 20
    assert row['customer_name'] == 'KH-N8N-01'
    assert len(events) == 1
    assert events[0]['event'] == 'Tạo đơn hàng'

    resp2 = client.post('/api/n8n/internal/rag/production-order-insert', json={
        'product_name': 'Missing product_code',
        'qty_to_produce': 5,
    })
    assert resp2.status_code == 400
    assert resp2.get_json()['message'] == 'Thiếu mã sản phẩm hoặc tên sản phẩm'

    resp3 = client.post('/api/n8n/internal/rag/production-order-insert', json={
        'product_code': 'SP-001',
        'product_name': 'Zero qty',
        'qty_to_produce': 0,
    })
    assert resp3.status_code == 400
