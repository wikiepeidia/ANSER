"""Integration tests for material batch CRUD (TRACE-01), traceability-chain
(TRACE-02), and expiring-batches (TRACE-06) — routes/inventory_routes.py.
"""
from datetime import datetime, timedelta

from core.sanxuat_db import get_connection


def test_create_list_update(logged_in_client):
    client = logged_in_client

    # Create a valid batch — materialName/unit resolved server-side.
    res = client.post('/api/material-batches', json={
        'materialCode': 'NVL-001',
        'supplierName': 'Dệt May Thành Công',
        'quantity': 100,
        'expiryDate': '2027-01-01',
        'notes': 'lô test đầu tiên',
    })
    data = res.get_json()
    assert res.status_code == 200
    assert data['success'] is True
    batch_id = data['id']
    assert data['code'] == f'LO-{2000 + batch_id}'

    # Invalid materialCode -> 400
    res = client.post('/api/material-batches', json={'materialCode': 'NVL-999', 'quantity': 10})
    assert res.status_code == 400

    # Missing materialCode -> 400
    res = client.post('/api/material-batches', json={'quantity': 10})
    assert res.status_code == 400

    # quantity <= 0 -> 400
    res = client.post('/api/material-batches', json={'materialCode': 'NVL-001', 'quantity': 0})
    assert res.status_code == 400
    assert res.get_json()['message'] == 'Số lượng phải lớn hơn 0'

    # Empty supplierName -> batch created with no supplier (no auto-create).
    res = client.post('/api/material-batches', json={
        'materialCode': 'NVL-003', 'quantity': 5, 'supplierName': '',
    })
    assert res.status_code == 200
    no_supplier_id = res.get_json()['id']

    # List and verify server-side resolved materialName/unit/supplierName.
    res = client.get('/api/material-batches')
    data = res.get_json()
    assert data['success'] is True
    created = next(b for b in data['batches'] if b['id'] == batch_id)
    assert created['materialName'] == 'Vải cotton'
    assert created['unit'] == 'm'
    assert created['supplierName'] == 'Dệt May Thành Công'
    no_supplier_batch = next(b for b in data['batches'] if b['id'] == no_supplier_id)
    assert no_supplier_batch['supplierId'] is None
    assert no_supplier_batch['supplierName'] == ''

    # New supplierName not matching any existing supplier -> auto-created
    # with a NCC-PENDING- placeholder code.
    res = client.post('/api/material-batches', json={
        'materialCode': 'NVL-002',
        'supplierName': 'Nhà Cung Cấp Test Mới XYZ',
        'quantity': 50,
    })
    assert res.status_code == 200
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT code FROM suppliers WHERE name = ?', ('Nhà Cung Cấp Test Mới XYZ',)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row['code'].startswith('NCC-PENDING-')

    # Update the first batch and verify the change is reflected on GET.
    res = client.put(f'/api/material-batches/{batch_id}', json={
        'materialCode': 'NVL-002',
        'supplierName': 'Chỉ May Phú Cường',
        'quantity': 200,
        'expiryDate': '2028-01-01',
        'notes': 'updated',
    })
    assert res.status_code == 200
    assert res.get_json()['success'] is True

    res = client.get('/api/material-batches')
    data = res.get_json()
    updated = next(b for b in data['batches'] if b['id'] == batch_id)
    assert updated['materialCode'] == 'NVL-002'
    assert updated['materialName'] == 'Chỉ may'
    assert updated['quantity'] == 200
    assert updated['supplierName'] == 'Chỉ May Phú Cường'

    # 404 for updating a nonexistent id.
    res = client.put('/api/material-batches/999999', json={'materialCode': 'NVL-001', 'quantity': 1})
    assert res.status_code == 404

    # Delete and verify absence from the default list.
    res = client.delete(f'/api/material-batches/{batch_id}')
    assert res.status_code == 200
    res = client.get('/api/material-batches')
    data = res.get_json()
    assert all(b['id'] != batch_id for b in data['batches'])


def test_trace_chain(logged_in_client):
    client = logged_in_client

    # A product + a BOM line referencing a material code this test controls.
    product_code = 'PRD-TRACE-01'
    res = client.post('/api/products', json={
        'code': product_code, 'name': 'Sản phẩm truy xuất test',
    })
    assert res.status_code == 200

    material_code = 'NVL-001'
    res = client.put(f'/api/bom/{product_code}', json={
        'lines': [{
            'code': material_code, 'name': 'Vải cotton', 'unit': 'm',
            'unitCost': 45000, 'qtyPerUnit': 2,
        }],
    })
    assert res.status_code == 200

    # A production order for that product.
    res = client.post('/api/production-orders', json={
        'productCode': product_code, 'productName': 'Sản phẩm truy xuất test', 'quantity': 10,
    })
    assert res.status_code == 200
    order_id = res.get_json()['id']

    # A material batch with the matching materialCode.
    res = client.post('/api/material-batches', json={'materialCode': material_code, 'quantity': 500})
    assert res.status_code == 200
    batch_id = res.get_json()['id']

    # Trace: order appears, isFinishedGoods = false (still draft).
    res = client.get(f'/api/material-batches/{batch_id}/trace')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    entry = next(e for e in data['consumingOrders'] if e['order']['id'] == order_id)
    assert entry['isFinishedGoods'] is False

    # Walk the full transition chain to 'completed'.
    for status in ('pending_approval', 'approved', 'in_progress', 'completed'):
        res = client.post(f'/api/production-orders/{order_id}/transition', json={'status': status})
        assert res.status_code == 200, res.get_json()

    res = client.get(f'/api/material-batches/{batch_id}/trace')
    data = res.get_json()
    entry = next(e for e in data['consumingOrders'] if e['order']['id'] == order_id)
    assert entry['isFinishedGoods'] is True

    # Soft-delete the batch — trace must still return 200 with the same
    # consumingOrders, not a 404 (Pitfall 2 / TRACE-02 historical guarantee).
    res = client.delete(f'/api/material-batches/{batch_id}')
    assert res.status_code == 200
    res = client.get(f'/api/material-batches/{batch_id}/trace')
    assert res.status_code == 200
    data = res.get_json()
    entry = next(e for e in data['consumingOrders'] if e['order']['id'] == order_id)
    assert entry['isFinishedGoods'] is True

    # A batch with no matching orders returns an empty (never null) list.
    res = client.post('/api/material-batches', json={'materialCode': 'NVL-007', 'quantity': 5})
    lonely_batch_id = res.get_json()['id']
    res = client.get(f'/api/material-batches/{lonely_batch_id}/trace')
    data = res.get_json()
    assert data['success'] is True
    assert data['consumingOrders'] == []


def test_expiring_batches(logged_in_client):
    client = logged_in_client
    today = datetime.now().date()

    def make_batch(days_offset=None, material='NVL-004'):
        payload = {'materialCode': material, 'quantity': 10}
        if days_offset is not None:
            payload['expiryDate'] = (today + timedelta(days=days_offset)).strftime('%Y-%m-%d')
        res = client.post('/api/material-batches', json=payload)
        assert res.status_code == 200
        return res.get_json()['id']

    expired_id = make_batch(-1)          # already expired
    soon_id = make_batch(3)              # expiring within default days=7
    later_id = make_batch(60)            # not within default, within days=90
    no_expiry_id = make_batch(None)      # no expiryDate -> never appears

    # Default days=7: already-expired + expiring-soon, most-urgent-first.
    res = client.get('/api/material-batches/expiring')
    assert res.status_code == 200
    data = res.get_json()
    ids = [b['id'] for b in data['batches']]
    assert expired_id in ids
    assert soon_id in ids
    assert later_id not in ids
    assert no_expiry_id not in ids
    assert ids.index(expired_id) < ids.index(soon_id)
    expired_entry = next(b for b in data['batches'] if b['id'] == expired_id)
    assert expired_entry['daysUntilExpiry'] < 0

    # days=90: superset including the far-future batch, still sorted.
    res = client.get('/api/material-batches/expiring?days=90')
    data = res.get_json()
    ids = [b['id'] for b in data['batches']]
    assert expired_id in ids and soon_id in ids and later_id in ids
    assert no_expiry_id not in ids
    assert ids.index(expired_id) < ids.index(soon_id) < ids.index(later_id)
