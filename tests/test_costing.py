"""Integration tests for production-order costing (COST-01, COST-02) —
routes/costing_routes.py.

Note: /api/material-batches validates materialCode against the fixed
MATERIALS_CATALOG (routes/inventory_routes.py), so these tests use real
catalog codes (NVL-001, NVL-002) as each product's BOM material code
instead of invented ones — bom_lines.unit_cost is set independently at BOM
save time and drives all costing math, so the catalog's own unitCost is
irrelevant here.
"""
from core.sanxuat_db import get_connection, now


def test_order_costing(logged_in_client):
    client = logged_in_client

    # BOM: 1 line, qtyPerUnit=2, unitCost=10000.
    resp = client.put('/api/bom/SP-COST-1', json={
        'lines': [
            {'code': 'NVL-001', 'name': 'Vai costing test', 'unit': 'm',
             'unitCost': 10000, 'qtyPerUnit': 2},
        ],
    })
    assert resp.status_code == 200

    resp = client.post('/api/products', json={
        'code': 'SP-COST-1', 'name': 'Ao Test Costing', 'price': 50000,
    })
    assert resp.status_code == 200

    resp = client.post('/api/production-orders', json={
        'productCode': 'SP-COST-1', 'productName': 'Ao Test Costing', 'quantity': 5,
    })
    assert resp.status_code == 200
    order_id = resp.get_json()['id']

    # No batch_usage yet -> materialCost only, wasteCost = 0.
    resp = client.get(f'/api/production-orders/{order_id}/costing')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    expected_material_cost = round(round(2 * 5, 2) * 10000)
    assert data['materialCost'] == expected_material_cost
    assert data['wasteCost'] == 0
    assert data['totalCost'] == expected_material_cost
    assert data['profitEstimate'] == round(50000 * 5 - expected_material_cost)

    # Record actual usage exceeding the planned qty (10) -> waste on the excess.
    resp = client.post('/api/material-batches', json={'materialCode': 'NVL-001', 'quantity': 20})
    assert resp.status_code == 200
    batch_id = resp.get_json()['id']

    conn = get_connection()
    try:
        conn.execute(
            'INSERT INTO batch_usage (batch_id, order_id, quantity_used, created_at) '
            'VALUES (?, ?, ?, ?)',
            (batch_id, order_id, 15, now()),
        )
        conn.commit()
    finally:
        conn.close()

    resp = client.get(f'/api/production-orders/{order_id}/costing')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['wasteCost'] == 50000
    assert data['totalCost'] == 150000
    assert data['profitEstimate'] == round(50000 * 5 - 150000)

    # Nonexistent order -> 404.
    resp = client.get('/api/production-orders/999999/costing')
    assert resp.status_code == 404
    assert resp.get_json()['success'] is False

    # A second order whose product has zero bom_lines -> no fabricated defaults.
    resp = client.post('/api/production-orders', json={
        'productCode': 'SP-COST-NOBOM', 'productName': 'San pham chua co BOM', 'quantity': 4,
    })
    assert resp.status_code == 200
    nobom_order_id = resp.get_json()['id']

    resp = client.get(f'/api/production-orders/{nobom_order_id}/costing')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['materialCost'] == 0
    assert data['wasteCost'] == 0
    assert data['lines'] == []
