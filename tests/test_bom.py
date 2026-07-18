"""Integration tests for the BOM backend (routes/production_routes.py).

Covers PROD-04 (full-replace BOM line management) and PROD-05 (material
requirement calculation with no fabricated defaults). Uses the module-scoped
`logged_in_client` fixture from tests/conftest.py against an isolated temp
SQLite DB.
"""


def test_bom_line_full_replace(logged_in_client):
    client = logged_in_client

    # PUT 2 valid lines for a product code.
    resp = client.put('/api/bom/SP-BOM-1', json={
        'lines': [
            {'code': 'NVL-01', 'name': 'Vai cotton', 'unit': 'm', 'unitCost': 50000, 'qtyPerUnit': 1.5},
            {'code': 'NVL-02', 'name': 'Chi may', 'unitCost': 2000, 'qtyPerUnit': 3},
        ],
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    lines = data['lines']
    assert len(lines) == 2
    l1 = next(l for l in lines if l['code'] == 'NVL-01')
    assert l1['name'] == 'Vai cotton'
    assert l1['unit'] == 'm'
    assert l1['unitCost'] == 50000
    assert l1['qtyPerUnit'] == 1.5
    l2 = next(l for l in lines if l['code'] == 'NVL-02')
    # unit omitted -> defaults to 'cái'
    assert l2['unit'] == 'cái'
    assert l2['unitCost'] == 2000
    assert l2['qtyPerUnit'] == 3

    # PUT again with a DIFFERENT set of 1 line for the same product code.
    resp = client.put('/api/bom/SP-BOM-1', json={
        'lines': [
            {'code': 'NVL-03', 'name': 'Khuy ao', 'unit': 'cái', 'unitCost': 500, 'qtyPerUnit': 5},
        ],
    })
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    # GET now returns only that 1 line (old 2 deleted, not left as orphans).
    resp = client.get('/api/bom/SP-BOM-1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert len(data['lines']) == 1
    assert data['lines'][0]['code'] == 'NVL-03'
    assert data['lines'][0]['name'] == 'Khuy ao'

    # PUT with an all-invalid line (empty code) -> 400, existing line untouched.
    resp = client.put('/api/bom/SP-BOM-1', json={
        'lines': [
            {'code': '', 'name': 'Bad line', 'unitCost': 100, 'qtyPerUnit': 1},
        ],
    })
    assert resp.status_code == 400
    data = resp.get_json()
    assert data['success'] is False
    assert data['message'] == 'Cần ít nhất 1 dòng nguyên vật liệu hợp lệ (mã, tên, định mức > 0)'

    resp = client.get('/api/bom/SP-BOM-1')
    data = resp.get_json()
    assert len(data['lines']) == 1
    assert data['lines'][0]['code'] == 'NVL-03'

    # GET for a product with no saved BOM -> empty array, not an error.
    resp = client.get('/api/bom/SP-NEVER-SAVED')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['lines'] == []


def test_bom_calculate_sum_and_empty_case(logged_in_client):
    client = logged_in_client

    resp = client.put('/api/bom/SP-BOM-CALC', json={
        'lines': [
            {'code': 'NVL-C1', 'name': 'Nguyen lieu C1', 'unit': 'kg', 'unitCost': 10000, 'qtyPerUnit': 2.5},
        ],
    })
    assert resp.status_code == 200

    resp = client.post('/api/bom/calculate', json={'productCode': 'SP-BOM-CALC', 'quantity': 7})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['quantity'] == 7
    assert len(data['lines']) == 1
    line = data['lines'][0]
    assert line['code'] == 'NVL-C1'
    assert line['qty'] == round(2.5 * 7, 2)
    assert line['lineCost'] == round(2.5 * 7 * 10000)
    assert data['totalCost'] == line['lineCost']

    # Product with NO bom_lines rows -> no fabricated defaults.
    resp = client.post('/api/bom/calculate', json={'productCode': 'SP-NEVER-SAVED-CALC', 'quantity': 4})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['lines'] == []
    assert data['totalCost'] == 0
    assert data['quantity'] == 4
