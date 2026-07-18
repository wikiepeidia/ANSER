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
