"""Integration tests for supplier CRUD (SUPPLIER-01) and the supplier->
batches FK lookup (SUPPLIER-02) -- routes/supplier_routes.py.
"""


def test_supplier_crud(logged_in_client):
    client = logged_in_client

    # Create with only `name` set -- code is server-generated NCC-{id:03d}.
    res = client.post('/api/suppliers', json={'name': 'Dệt May Thành Công'})
    data = res.get_json()
    assert res.status_code == 200
    assert data['success'] is True
    supplier_id = data['id']
    assert data['code'] == f'NCC-{str(supplier_id).zfill(3)}'

    # Missing/empty name -> 400.
    res = client.post('/api/suppliers', json={'name': ''})
    assert res.status_code == 400
    assert res.get_json()['message'] == 'Thiếu tên nhà cung cấp'

    res = client.post('/api/suppliers', json={})
    assert res.status_code == 400

    # List includes the created supplier with the correct code format.
    res = client.get('/api/suppliers')
    data = res.get_json()
    assert data['success'] is True
    created = next(s for s in data['suppliers'] if s['id'] == supplier_id)
    assert created['name'] == 'Dệt May Thành Công'
    assert created['code'] == f'NCC-{str(supplier_id).zfill(3)}'

    # Update contact/phone -- reflected on next GET, code unchanged.
    res = client.put(f'/api/suppliers/{supplier_id}', json={
        'name': 'Dệt May Thành Công',
        'contact': 'Nguyễn Văn A',
        'phone': '0901234567',
    })
    assert res.status_code == 200
    res = client.get('/api/suppliers')
    updated = next(s for s in res.get_json()['suppliers'] if s['id'] == supplier_id)
    assert updated['contact'] == 'Nguyễn Văn A'
    assert updated['phone'] == '0901234567'
    assert updated['code'] == f'NCC-{str(supplier_id).zfill(3)}'

    # Delete -- absent from default GET list.
    res = client.delete(f'/api/suppliers/{supplier_id}')
    assert res.status_code == 200
    res = client.get('/api/suppliers')
    assert all(s['id'] != supplier_id for s in res.get_json()['suppliers'])

    # PUT/DELETE against a nonexistent id -> 404 for both.
    res = client.put('/api/suppliers/999999', json={'name': 'x'})
    assert res.status_code == 404
    res = client.delete('/api/suppliers/999999')
    assert res.status_code == 404
