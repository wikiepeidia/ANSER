"""Integration tests for material batch CRUD (TRACE-01), traceability-chain
(TRACE-02), and expiring-batches (TRACE-06) — routes/inventory_routes.py.
"""
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
