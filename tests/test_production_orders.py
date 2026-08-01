"""Integration tests for the production-orders backend (routes/production_routes.py).

Covers PROD-01 (create/list/filter), PROD-02 (status-transition graph),
PROD-03 (update + soft delete). Uses the module-scoped `logged_in_client`
fixture from tests/conftest.py against an isolated temp SQLite DB.
"""
from core.sanxuat_db import get_connection, now


def test_create_and_filter_list(logged_in_client):
    client = logged_in_client

    resp = client.post('/api/production-orders', json={
        'productCode': 'SP-001',
        'productName': 'Ao thun',
        'quantity': 10,
        'unit': 'cái',
        'customerName': 'Khach A',
        'notes': 'ghi chu don 1',
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    order_id = data['id']
    assert data['code'] == f'DH-{1000 + order_id}'

    # Second order with a different status, inserted directly (transition
    # endpoint doesn't exist until Task 2) so filtering can be exercised now.
    conn = get_connection()
    try:
        conn.execute(
            'INSERT INTO production_orders (code, product_code, product_name, quantity, unit, '
            'customer_name, notes, status, created_by, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            ('DH-9001', 'SP-002', 'Quan jean', 5, 'cái', 'Khach B', '', 'approved', 1, now()),
        )
        conn.commit()
    finally:
        conn.close()

    resp = client.get('/api/production-orders')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    all_orders = data['orders']
    created = next(o for o in all_orders if o['id'] == order_id)
    assert created['code'] == f'DH-{1000 + order_id}'
    assert created['productCode'] == 'SP-001'
    assert created['productName'] == 'Ao thun'
    assert created['quantity'] == 10
    assert created['unit'] == 'cái'
    assert created['customerName'] == 'Khach A'
    assert created['notes'] == 'ghi chu don 1'
    assert created['status'] == 'draft'
    assert any(o['code'] == 'DH-9001' and o['status'] == 'approved' for o in all_orders)

    resp = client.get('/api/production-orders?status=draft')
    data = resp.get_json()
    assert all(o['status'] == 'draft' for o in data['orders'])
    assert any(o['id'] == order_id for o in data['orders'])
    assert not any(o['code'] == 'DH-9001' for o in data['orders'])

    resp = client.get('/api/production-orders?status=approved')
    data = resp.get_json()
    assert all(o['status'] == 'approved' for o in data['orders'])
    assert any(o['code'] == 'DH-9001' for o in data['orders'])

    resp = client.post('/api/production-orders', json={'productName': 'x', 'quantity': 1})
    assert resp.status_code == 400
    assert 'Thiếu mã sản phẩm' in resp.get_json()['message']

    resp = client.post('/api/production-orders', json={
        'productCode': 'SP-003', 'productName': 'y', 'quantity': 0,
    })
    assert resp.status_code == 400
    assert 'Số lượng phải lớn hơn 0' in resp.get_json()['message']


def test_update_and_soft_delete(logged_in_client):
    client = logged_in_client

    resp = client.post('/api/production-orders', json={
        'productCode': 'SP-010',
        'productName': 'San pham test',
        'quantity': 3,
    })
    order_id = resp.get_json()['id']

    resp = client.put(f'/api/production-orders/{order_id}', json={
        'productCode': 'SP-010-B',
        'productName': 'San pham sua',
        'quantity': 7,
        'unit': 'hộp',
        'customerName': 'Khach moi',
        'notes': 'note moi',
        'status': 'completed',  # must be silently ignored
    })
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    resp = client.get('/api/production-orders')
    order = next(o for o in resp.get_json()['orders'] if o['id'] == order_id)
    assert order['productCode'] == 'SP-010-B'
    assert order['productName'] == 'San pham sua'
    assert order['quantity'] == 7
    assert order['unit'] == 'hộp'
    assert order['customerName'] == 'Khach moi'
    assert order['notes'] == 'note moi'
    assert order['status'] == 'draft'  # unchanged despite status in request body

    resp = client.put('/api/production-orders/999999', json={
        'productCode': 'x', 'productName': 'y', 'quantity': 1,
    })
    assert resp.status_code == 404
    assert resp.get_json()['success'] is False

    resp = client.delete(f'/api/production-orders/{order_id}')
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    resp = client.get('/api/production-orders')
    ids = [o['id'] for o in resp.get_json()['orders']]
    assert order_id not in ids


def test_status_transitions(logged_in_client):
    client = logged_in_client

    # Seed a product matching the order's productCode so the completion
    # side-effect (stock_quantity increment) has somewhere to land.
    resp = client.post('/api/products', json={
        'code': 'SP-100', 'name': 'San pham hoan thanh', 'stock_quantity': 5,
    })
    assert resp.status_code == 200

    resp = client.post('/api/production-orders', json={
        'productCode': 'SP-100', 'productName': 'San pham hoan thanh', 'quantity': 20,
    })
    order_id = resp.get_json()['id']

    # draft -> in_progress directly (skipping approval) is rejected
    resp = client.post(f'/api/production-orders/{order_id}/transition', json={'status': 'in_progress'})
    assert resp.status_code == 409
    body = resp.get_json()
    assert body['success'] is False
    assert 'Không thể chuyển từ' in body['message']

    # full valid sequence: draft -> pending_approval -> approved -> in_progress -> completed
    resp = client.post(f'/api/production-orders/{order_id}/transition', json={'status': 'pending_approval'})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    # self-transition (re-submitting the same status) is rejected, not a no-op
    resp = client.post(f'/api/production-orders/{order_id}/transition', json={'status': 'pending_approval'})
    assert resp.status_code == 409

    resp = client.post(f'/api/production-orders/{order_id}/transition', json={'status': 'approved'})
    assert resp.status_code == 200

    resp = client.post(f'/api/production-orders/{order_id}/transition', json={'status': 'in_progress'})
    assert resp.status_code == 200

    resp = client.post(f'/api/production-orders/{order_id}/transition', json={'status': 'completed'})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    # products.stock_quantity increased by the order's quantity (5 + 20 = 25)
    resp = client.get('/api/products')
    product = next(p for p in resp.get_json()['products'] if p['code'] == 'SP-100')
    assert product['stock_quantity'] == 25

    # per-order events: ascending time order, includes create + completion events
    resp = client.get(f'/api/production-orders/{order_id}/events')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    events = data['events']
    event_names = [e['event'] for e in events]
    assert event_names[0] == 'Tạo đơn hàng'
    assert 'Hoàn thành' in event_names
    assert 'Nhập kho thành phẩm' in event_names
    assert all(e['orderId'] == order_id for e in events)
    timestamps = [e['ts'] for e in events]
    assert timestamps == sorted(timestamps)

    # bulk events endpoint (Store.loadProductionOrders()'s Promise.all partner call)
    resp = client.get('/api/production-orders/events')
    assert resp.status_code == 200
    bulk = resp.get_json()['events']
    assert any(e['orderId'] == order_id and e['event'] == 'Tạo đơn hàng' for e in bulk)

    # transitioning a terminal (completed) order is rejected
    resp = client.post(f'/api/production-orders/{order_id}/transition', json={'status': 'cancelled'})
    assert resp.status_code == 409


def _drive_to_completed(client, order_id):
    """Shared helper: drives an order through the full valid transition
    sequence (draft -> pending_approval -> approved -> in_progress ->
    completed), asserting 200 at every step, and returns the final
    'completed' transition's response JSON."""
    for status in ('pending_approval', 'approved', 'in_progress', 'completed'):
        resp = client.post(f'/api/production-orders/{order_id}/transition', json={'status': status})
        assert resp.status_code == 200, f'transition to {status} failed: {resp.get_json()}'
    return resp.get_json()


def test_completion_fifo_oldest_batch_first(logged_in_client):
    client = logged_in_client

    resp = client.post('/api/products', json={'code': 'SP-FIFO-1', 'name': 'SP FIFO 1'})
    assert resp.status_code == 200

    resp = client.put('/api/bom/SP-FIFO-1', json={
        'lines': [
            {'code': 'NVL-001', 'name': 'Vai FIFO', 'unit': 'm', 'unitCost': 1000, 'qtyPerUnit': 3},
        ],
    })
    assert resp.status_code == 200

    resp = client.post('/api/production-orders', json={
        'productCode': 'SP-FIFO-1', 'productName': 'SP FIFO 1', 'quantity': 4,
    })
    assert resp.status_code == 200
    order_id = resp.get_json()['id']  # plannedQty = round(3*4, 2) = 12

    resp = client.post('/api/material-batches', json={'materialCode': 'NVL-001', 'quantity': 5})
    assert resp.status_code == 200
    older_batch_id = resp.get_json()['id']

    resp = client.post('/api/material-batches', json={'materialCode': 'NVL-001', 'quantity': 20})
    assert resp.status_code == 200
    newer_batch_id = resp.get_json()['id']

    # Control FIFO order deterministically (POST doesn't accept a
    # client-supplied import_date).
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE material_batches SET import_date = '2026-01-01 00:00:00' WHERE id = ?",
            (older_batch_id,),
        )
        conn.execute(
            "UPDATE material_batches SET import_date = '2026-06-01 00:00:00' WHERE id = ?",
            (newer_batch_id,),
        )
        conn.commit()
    finally:
        conn.close()

    resp = client.post(f'/api/material-batches/{older_batch_id}/qc-result', json={'qcStatus': 'passed'})
    assert resp.status_code == 200
    resp = client.post(f'/api/material-batches/{newer_batch_id}/qc-result', json={'qcStatus': 'passed'})
    assert resp.status_code == 200

    final = _drive_to_completed(client, order_id)
    assert final['materialShortfalls'] == []

    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT batch_id, quantity_used FROM batch_usage WHERE order_id = ? ORDER BY batch_id',
            (order_id,),
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 2
    usage_by_batch = {r['batch_id']: r['quantity_used'] for r in rows}
    assert usage_by_batch[older_batch_id] == 5
    assert usage_by_batch[newer_batch_id] == 7

    resp = client.get(f'/api/production-orders/{order_id}/costing')
    assert resp.status_code == 200
    data = resp.get_json()
    line = next(l for l in data['lines'] if l['materialCode'] == 'NVL-001')
    assert line['actualUsed'] == 12
    assert line['wasteCostLine'] == 0
    assert data['wasteCost'] == 0

    # Zero-BOM product completes cleanly, inserts zero batch_usage rows.
    resp = client.post('/api/production-orders', json={
        'productCode': 'SP-FIFO-NOBOM', 'productName': 'SP FIFO NoBOM', 'quantity': 2,
    })
    assert resp.status_code == 200
    nobom_order_id = resp.get_json()['id']

    final_nobom = _drive_to_completed(client, nobom_order_id)
    assert final_nobom['materialShortfalls'] == []

    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT id FROM batch_usage WHERE order_id = ?', (nobom_order_id,)
        ).fetchall()
    finally:
        conn.close()
    assert rows == []
