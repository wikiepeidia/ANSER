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


def test_lab_result_insert(client):
    batch_resp = client.post('/api/n8n/internal/rag/material-batch-insert', json={
        'material_code': 'NVL-002',
        'qty_kg': 30,
        'farmer': 'NCC Lab Test',
    })
    code = batch_resp.get_json()['code']

    resp = client.post('/api/n8n/internal/rag/lab-result-insert', json={
        'batch_code': code,
        'pesticide_ok': True,
        'heavy_metal_ok': True,
        'tested_by': 'Nguyễn Văn A',
        'cynarin_pct': 5.2,
        'mold_cfu_g': 100,
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['status'] == 'passed'
    assert body['batch_code'] == code
    assert body['sellable'] is True
    assert body['reasons'] == []

    conn = get_connection()
    try:
        batch_id = conn.execute(
            'SELECT id FROM material_batches WHERE batch_code = ?', (code,),
        ).fetchone()['id']
        rows = conn.execute(
            'SELECT result, detail FROM qc_results WHERE batch_id = ?', (batch_id,),
        ).fetchall()
        batch_row = conn.execute(
            'SELECT qc_status FROM material_batches WHERE id = ?', (batch_id,),
        ).fetchone()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]['result'] == 'pass'
    assert rows[0]['detail'] == 'Kiểm định bởi Nguyễn Văn A'
    assert batch_row['qc_status'] == 'passed'

    resp2 = client.post('/api/n8n/internal/rag/lab-result-insert', json={
        'batch_code': code,
        'pesticide_ok': True,
        'heavy_metal_ok': False,
        'tested_by': 'Trần B',
    })
    assert resp2.status_code == 201
    body2 = resp2.get_json()
    assert body2['status'] == 'failed'
    assert body2['sellable'] is False
    assert body2['reasons'] == ['heavy_metal_ok']

    conn = get_connection()
    try:
        rows2 = conn.execute(
            'SELECT result FROM qc_results WHERE batch_id = ?', (batch_id,),
        ).fetchall()
        batch_row2 = conn.execute(
            'SELECT qc_status FROM material_batches WHERE id = ?', (batch_id,),
        ).fetchone()
    finally:
        conn.close()
    assert len(rows2) == 2
    assert batch_row2['qc_status'] == 'failed'


def test_lab_result_insert_unknown_batch(client):
    resp = client.post('/api/n8n/internal/rag/lab-result-insert', json={
        'batch_code': 'LO-999999',
        'pesticide_ok': True,
        'heavy_metal_ok': True,
        'tested_by': 'X',
    })
    assert resp.status_code == 404
    assert resp.get_json()['message'] == 'Không tìm thấy lô nguyên liệu theo mã: LO-999999'


def test_process_event(client):
    batch_resp = client.post('/api/n8n/internal/rag/material-batch-insert', json={
        'material_code': 'NVL-003',
        'qty_kg': 15,
        'farmer': 'NCC Process Test',
    })
    code = batch_resp.get_json()['code']

    resp = client.post('/api/n8n/internal/rag/process-event', json={
        'event': 'Bắt đầu sản xuất',
        'batch_code': code,
        'order_code': 'IGNORED',
        'shift': 'sáng',
        'temp_c': 25,
        'duration_min': 60,
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['event'] == 'Bắt đầu sản xuất'
    assert body['note'] == ''
    assert 'batch_id' in body

    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT event, note FROM material_batch_events WHERE batch_id = ?',
            (body['batch_id'],),
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]['event'] == 'Bắt đầu sản xuất'
    assert not rows[0]['note']

    resp2 = client.post('/api/n8n/internal/rag/process-event', json={
        'event': '',
        'batch_code': code,
    })
    assert resp2.status_code == 400
    assert resp2.get_json()['message'] == 'Thiếu tên sự kiện quy trình'

    resp3 = client.post('/api/n8n/internal/rag/process-event', json={
        'event': 'Bắt đầu sản xuất',
        'batch_code': 'LO-999999',
    })
    assert resp3.status_code == 404
    assert resp3.get_json()['message'] == 'Không tìm thấy lô nguyên liệu theo mã: LO-999999'


def test_unrouted_action_falls_through(client):
    resp = client.post('/api/n8n/internal/rag/pending-review', json={
        'foo': 'bar', 'reason': 'low OCR confidence',
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['success'] is True
    assert body['action'] == 'pending-review'
    assert body['received'] == {'foo': 'bar', 'reason': 'low OCR confidence'}
    assert 'id' in body

    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT action FROM automation_events WHERE id = ?', (body['id'],),
        ).fetchone()
    finally:
        conn.close()
    assert row['action'] == 'rag:pending-review'
