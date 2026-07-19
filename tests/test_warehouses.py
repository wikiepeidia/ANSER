"""Integration tests for routes/warehouse_routes.py — warehouse/location
CRUD, the SUM(quantity_delta) current-stock projection, atomic stock
transfer, and stocktake adjustment (TRACE-03/04/05).
"""


def test_warehouse_location_crud(logged_in_client):
    # Create a warehouse.
    resp = logged_in_client.post('/api/warehouses', json={
        'code': 'KHO-HN', 'name': 'Kho Hà Nội', 'address': '123 Đường ABC',
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['success'] is True
    assert body['code'] == 'KHO-HN'
    warehouse_id = body['id']

    # Duplicate code -> 400.
    resp = logged_in_client.post('/api/warehouses', json={
        'code': 'KHO-HN', 'name': 'Kho Hà Nội 2',
    })
    assert resp.status_code == 400

    # List includes it.
    resp = logged_in_client.get('/api/warehouses')
    assert resp.status_code == 200
    codes = [w['code'] for w in resp.get_json()['warehouses']]
    assert 'KHO-HN' in codes

    # Update.
    resp = logged_in_client.put(f'/api/warehouses/{warehouse_id}', json={
        'code': 'KHO-HN', 'name': 'Kho Hà Nội (Updated)', 'address': '456 Đường XYZ',
    })
    assert resp.status_code == 200
    resp = logged_in_client.get('/api/warehouses')
    names = {w['id']: w['name'] for w in resp.get_json()['warehouses']}
    assert names[warehouse_id] == 'Kho Hà Nội (Updated)'

    # Create a location under it.
    resp = logged_in_client.post('/api/warehouse-locations', json={
        'warehouseId': warehouse_id, 'code': 'A1', 'name': 'Khu A1 - Kệ 1',
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['success'] is True
    location_id = body['id']

    # Location under a nonexistent warehouse -> 404.
    resp = logged_in_client.post('/api/warehouse-locations', json={
        'warehouseId': 999999, 'code': 'B1', 'name': 'Khu B1',
    })
    assert resp.status_code == 404

    # List locations.
    resp = logged_in_client.get(f'/api/warehouses/{warehouse_id}/locations')
    assert resp.status_code == 200
    loc_codes = [loc['code'] for loc in resp.get_json()['locations']]
    assert 'A1' in loc_codes

    # Update + delete location.
    resp = logged_in_client.put(f'/api/warehouse-locations/{location_id}', json={
        'code': 'A1', 'name': 'Khu A1 - Kệ 1 (Updated)',
    })
    assert resp.status_code == 200

    resp = logged_in_client.delete(f'/api/warehouse-locations/{location_id}')
    assert resp.status_code == 200
    resp = logged_in_client.get(f'/api/warehouses/{warehouse_id}/locations')
    loc_ids = [loc['id'] for loc in resp.get_json()['locations']]
    assert location_id not in loc_ids

    # Delete warehouse.
    resp = logged_in_client.delete(f'/api/warehouses/{warehouse_id}')
    assert resp.status_code == 200
    resp = logged_in_client.get('/api/warehouses')
    wh_ids = [w['id'] for w in resp.get_json()['warehouses']]
    assert warehouse_id not in wh_ids
