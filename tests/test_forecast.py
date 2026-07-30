"""Tests for GET /api/forecast/materials (N8N-03).

Trailing-average material-demand forecast: velocity from recent
production_orders, projected over horizonDays, multiplied by
bom_lines.qty_per_unit. See routes/forecast_routes.py.
"""


def test_forecast_single_product_trailing_average(logged_in_client):
    client = logged_in_client

    resp = client.put('/api/bom/SP-FORECAST-1', json={
        'lines': [
            {'code': 'NVL-FORECAST-A', 'name': 'Nguyen lieu du bao A', 'unit': 'kg',
             'unitCost': 45000, 'qtyPerUnit': 3},
        ],
    })
    assert resp.status_code == 200

    resp = client.post('/api/production-orders', json={
        'productCode': 'SP-FORECAST-1', 'productName': 'SP du bao 1', 'quantity': 10,
    })
    assert resp.status_code == 200
    resp = client.post('/api/production-orders', json={
        'productCode': 'SP-FORECAST-1', 'productName': 'SP du bao 1', 'quantity': 20,
    })
    assert resp.status_code == 200

    resp = client.get('/api/forecast/materials?windowDays=30&horizonDays=30')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['method'] == 'trailing_average'
    assert isinstance(body['note'], str) and body['note']

    product = next(p for p in body['products'] if p['productCode'] == 'SP-FORECAST-1')
    assert product['quantityInWindow'] == 30
    assert product['ordersInWindow'] == 2
    assert product['velocityPerDay'] == 1.0
    assert product['projectedQty'] == 30.0
    assert product['lines'][0]['forecastQty'] == 90.0
    assert product['lines'][0]['forecastCost'] == 4050000

    material = next(m for m in body['materials'] if m['materialCode'] == 'NVL-FORECAST-A')
    assert material['totalForecastQty'] == 90.0
    assert material['totalForecastCost'] == 4050000

    resp = client.get('/api/forecast/materials?windowDays=30&horizonDays=15')
    assert resp.status_code == 200
    body = resp.get_json()
    product = next(p for p in body['products'] if p['productCode'] == 'SP-FORECAST-1')
    assert product['projectedQty'] == 15.0
    assert product['lines'][0]['forecastQty'] == 45.0


def test_forecast_zero_orders_in_window_no_fabrication(logged_in_client):
    client = logged_in_client

    resp = client.get('/api/forecast/materials?productCode=SP-FORECAST-NONE&windowDays=30')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['products'] == []
    assert body['materials'] == []


def test_forecast_invalid_window_params(logged_in_client):
    client = logged_in_client

    resp = client.get('/api/forecast/materials?windowDays=0')
    assert resp.status_code == 400

    resp = client.get('/api/forecast/materials?windowDays=abc')
    assert resp.status_code == 400

    resp = client.get('/api/forecast/materials?windowDays=30&horizonDays=0')
    assert resp.status_code == 400


def test_forecast_product_code_filter_scoped(logged_in_client):
    client = logged_in_client

    resp = client.get('/api/forecast/materials?productCode=SP-FORECAST-1&windowDays=30')
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body['products']) == 1
    assert body['products'][0]['productCode'] == 'SP-FORECAST-1'
