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


def test_supplier_batches_fk(logged_in_client):
    client = logged_in_client

    # Create a supplier, capturing its exact name.
    res = client.post('/api/suppliers', json={'name': 'Nhà Cung Cấp FK Test'})
    data = res.get_json()
    assert res.status_code == 200
    supplier_id = data['id']

    # 2 batches whose supplierName exactly matches the supplier's name --
    # _resolve_supplier must match the existing row, not auto-create a new
    # one (proven by asserting supplierId equals the created supplier's id).
    res1 = client.post('/api/material-batches', json={
        'materialCode': 'NVL-001', 'supplierName': 'Nhà Cung Cấp FK Test', 'quantity': 10,
    })
    batch1 = res1.get_json()
    assert res1.status_code == 200
    res2 = client.post('/api/material-batches', json={
        'materialCode': 'NVL-002', 'supplierName': 'Nhà Cung Cấp FK Test', 'quantity': 20,
    })
    batch2 = res2.get_json()
    assert res2.status_code == 200

    res_list = client.get('/api/material-batches')
    list_data = res_list.get_json()['batches']
    b1 = next(b for b in list_data if b['id'] == batch1['id'])
    b2 = next(b for b in list_data if b['id'] == batch2['id'])
    assert b1['supplierId'] == supplier_id
    assert b2['supplierId'] == supplier_id

    # A 3rd batch with a different, unrelated supplierName.
    res3 = client.post('/api/material-batches', json={
        'materialCode': 'NVL-003', 'supplierName': 'Nhà Cung Cấp Khác Không Liên Quan',
        'quantity': 5,
    })
    batch3 = res3.get_json()
    assert res3.status_code == 200

    # GET .../batches for the first supplier returns exactly the 2 matching
    # batches, not the 3rd.
    res = client.get(f'/api/suppliers/{supplier_id}/batches')
    data = res.get_json()
    assert res.status_code == 200
    assert data['success'] is True
    returned_ids = {b['id'] for b in data['batches']}
    assert returned_ids == {batch1['id'], batch2['id']}
    assert batch3['id'] not in returned_ids

    # Nonexistent supplier id -> 404.
    res = client.get('/api/suppliers/999999/batches')
    assert res.status_code == 404
    assert res.get_json()['message'] == 'Không tìm thấy nhà cung cấp'

    # Soft-delete the first supplier -- lookup still returns 200 with the
    # same 2 batches (existence check must not filter is_deleted).
    res = client.delete(f'/api/suppliers/{supplier_id}')
    assert res.status_code == 200
    res = client.get(f'/api/suppliers/{supplier_id}/batches')
    assert res.status_code == 200
    returned_ids = {b['id'] for b in res.get_json()['batches']}
    assert returned_ids == {batch1['id'], batch2['id']}

    # Batches' supplierName still resolves correctly on GET /api/material-
    # batches despite the referenced supplier being soft-deleted.
    res = client.get('/api/material-batches')
    list_data = res.get_json()['batches']
    b1 = next(b for b in list_data if b['id'] == batch1['id'])
    b2 = next(b for b in list_data if b['id'] == batch2['id'])
    assert b1['supplierName'] == 'Nhà Cung Cấp FK Test'
    assert b2['supplierName'] == 'Nhà Cung Cấp FK Test'
