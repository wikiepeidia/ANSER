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


def _make_warehouse_with_location(client, code_prefix):
    resp = client.post('/api/warehouses', json={'code': f'{code_prefix}-WH', 'name': f'{code_prefix} Warehouse'})
    warehouse_id = resp.get_json()['id']
    resp = client.post('/api/warehouse-locations', json={
        'warehouseId': warehouse_id, 'code': f'{code_prefix}-LOC', 'name': f'{code_prefix} Location',
    })
    location_id = resp.get_json()['id']
    return warehouse_id, location_id


def test_transfer_stock(logged_in_client):
    source_wh, source_loc = _make_warehouse_with_location(logged_in_client, 'SRC')
    dest_wh, dest_loc = _make_warehouse_with_location(logged_in_client, 'DST')
    product_code = 'NVL-001'

    # Seed initial stock at the source via stocktake (ledger starts empty).
    resp = logged_in_client.post('/api/warehouse-stock/stocktake', json={
        'warehouseId': source_wh, 'locationId': source_loc, 'productCode': product_code,
        'countedQty': 100,
    })
    assert resp.status_code == 200

    # Transfer part of the seeded stock.
    resp = logged_in_client.post('/api/warehouse-stock/transfer', json={
        'productCode': product_code,
        'fromWarehouseId': source_wh, 'fromLocationId': source_loc,
        'toWarehouseId': dest_wh, 'toLocationId': dest_loc,
        'quantity': 30, 'note': 'test transfer',
    })
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    # Ledger at the source: 1 adjustment (seed) + 1 transfer_out = 2 rows.
    resp = logged_in_client.get(f'/api/warehouse-stock/ledger?warehouseId={source_wh}')
    entries = resp.get_json()['entries']
    assert len(entries) == 2

    # Balances reflect the transfer.
    resp = logged_in_client.get('/api/warehouse-stock')
    stock = resp.get_json()['stock']
    source_row = next(s for s in stock if s['warehouseId'] == source_wh and s['locationId'] == source_loc)
    dest_row = next(s for s in stock if s['warehouseId'] == dest_wh and s['locationId'] == dest_loc)
    assert source_row['quantity'] == 70
    assert dest_row['quantity'] == 30

    # Insufficient stock -> 409.
    resp = logged_in_client.post('/api/warehouse-stock/transfer', json={
        'productCode': product_code,
        'fromWarehouseId': source_wh, 'fromLocationId': source_loc,
        'toWarehouseId': dest_wh, 'toLocationId': dest_loc,
        'quantity': 1000,
    })
    assert resp.status_code == 409
    assert 'Không đủ tồn kho tại vị trí nguồn' in resp.get_json()['message']

    # Same source/dest location -> 400.
    resp = logged_in_client.post('/api/warehouse-stock/transfer', json={
        'productCode': product_code,
        'fromWarehouseId': source_wh, 'fromLocationId': source_loc,
        'toWarehouseId': source_wh, 'toLocationId': source_loc,
        'quantity': 10,
    })
    assert resp.status_code == 400
    assert 'Vị trí nguồn và đích phải khác nhau' in resp.get_json()['message']

    # quantity=0 -> 400.
    resp = logged_in_client.post('/api/warehouse-stock/transfer', json={
        'productCode': product_code,
        'fromWarehouseId': source_wh, 'fromLocationId': source_loc,
        'toWarehouseId': dest_wh, 'toLocationId': dest_loc,
        'quantity': 0,
    })
    assert resp.status_code == 400


def test_stocktake_adjustment(logged_in_client):
    warehouse_id, location_id = _make_warehouse_with_location(logged_in_client, 'STK')
    product_code = 'NVL-002'

    # Brand-new triple, no prior stock.
    resp = logged_in_client.post('/api/warehouse-stock/stocktake', json={
        'warehouseId': warehouse_id, 'locationId': location_id, 'productCode': product_code,
        'countedQty': 20,
    })
    assert resp.status_code == 200

    resp = logged_in_client.get('/api/warehouse-stock')
    stock = resp.get_json()['stock']
    row = next(s for s in stock if s['warehouseId'] == warehouse_id and s['locationId'] == location_id
               and s['productCode'] == product_code)
    assert row['quantity'] == 20

    # Recount to 0 -> position disappears (HAVING SUM(...) > 0).
    resp = logged_in_client.post('/api/warehouse-stock/stocktake', json={
        'warehouseId': warehouse_id, 'locationId': location_id, 'productCode': product_code,
        'countedQty': 0,
    })
    assert resp.status_code == 200

    resp = logged_in_client.get('/api/warehouse-stock')
    stock = resp.get_json()['stock']
    matches = [s for s in stock if s['warehouseId'] == warehouse_id and s['locationId'] == location_id
               and s['productCode'] == product_code]
    assert matches == []

    # Negative countedQty -> 400.
    resp = logged_in_client.post('/api/warehouse-stock/stocktake', json={
        'warehouseId': warehouse_id, 'locationId': location_id, 'productCode': product_code,
        'countedQty': -5,
    })
    assert resp.status_code == 400
    assert resp.get_json()['message'] == 'Số lượng đếm không hợp lệ'
