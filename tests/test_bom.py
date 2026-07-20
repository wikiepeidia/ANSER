"""Integration tests for the BOM backend (routes/production_routes.py).

Covers PROD-04 (full-replace BOM line management), PROD-05 (material
requirement calculation with no fabricated defaults), and QC-02 (the
passed-QC stock gate on calculate_bom(), 02.1-03). Uses the module-scoped
`logged_in_client` fixture from tests/conftest.py against an isolated temp
SQLite DB.
"""

from core.sanxuat_db import get_connection


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


# ── QC-02 gating (02.1-03) ────────────────────────────────────────────────
# A BOM line only blocks the calculate request when its material HAS at
# least one existing material_batches row AND that material's passed-QC
# quantity is insufficient for the requested amount. A material that has
# never been received (zero batches at all) is never blocked — see
# 02.1-CONTEXT.md's locked QC-02 resolution.

def test_bom_calculate_qc_gating_zero_batches_not_blocked(logged_in_client):
    client = logged_in_client

    resp = client.put('/api/bom/SP-QC-ZERO', json={
        'lines': [
            {'code': 'NVL-001', 'name': 'Vai cotton', 'unit': 'm', 'unitCost': 45000, 'qtyPerUnit': 2},
        ],
    })
    assert resp.status_code == 200

    # NVL-001 has never been posted to /api/material-batches in this test
    # -> zero material_batches rows -> must NOT be blocked, regardless of
    # the requested quantity.
    resp = client.post('/api/bom/calculate', json={'productCode': 'SP-QC-ZERO', 'quantity': 10})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert 'blockedMaterials' not in data
    assert len(data['lines']) == 1
    assert data['lines'][0]['code'] == 'NVL-001'
    assert data['quantity'] == 10


def test_bom_calculate_qc_gating_blocks_insufficient(logged_in_client):
    client = logged_in_client

    resp = client.put('/api/bom/SP-QC-BLOCK', json={
        'lines': [
            {'code': 'NVL-002', 'name': 'Chi may', 'unit': 'cuộn', 'unitCost': 8000, 'qtyPerUnit': 1},
        ],
    })
    assert resp.status_code == 200

    # A real batch exists for NVL-002 but its qc_status defaults to
    # 'pending' (never touched by this test) -> available_passed is 0.
    resp = client.post('/api/material-batches', json={'materialCode': 'NVL-002', 'quantity': 5})
    assert resp.status_code == 200

    resp = client.post('/api/bom/calculate', json={'productCode': 'SP-QC-BLOCK', 'quantity': 3})
    assert resp.status_code == 409
    data = resp.get_json()
    assert data['success'] is False
    assert data['message'] == 'Một số nguyên vật liệu chưa đủ số lượng đạt kiểm định QC'
    assert len(data['blockedMaterials']) == 1
    blocked = data['blockedMaterials'][0]
    assert blocked['materialCode'] == 'NVL-002'
    assert blocked['required'] == round(1 * 3, 2)
    assert blocked['availablePassed'] == 0


def _mark_batch_passed(batch_id):
    """Directly set a batch's qc_status to 'passed' via the DB connection --
    no QC-recording route exists in this plan's scope (02.1-01/02 own that)."""
    conn = get_connection()
    try:
        conn.execute('UPDATE material_batches SET qc_status = ? WHERE id = ?', ('passed', batch_id))
        conn.commit()
    finally:
        conn.close()


def test_bom_calculate_qc_gating_sufficient_passed_allows(logged_in_client):
    client = logged_in_client

    resp = client.put('/api/bom/SP-QC-SUFFICIENT', json={
        'lines': [
            {'code': 'NVL-003', 'name': 'Khuy nhua', 'unit': 'cái', 'unitCost': 500, 'qtyPerUnit': 2},
        ],
    })
    assert resp.status_code == 200

    # Required qty for quantity=5 is 2 * 5 = 10 -> batch quantity set to
    # exactly that (boundary case: required == available_passed, not >).
    resp = client.post('/api/material-batches', json={'materialCode': 'NVL-003', 'quantity': 10})
    assert resp.status_code == 200
    _mark_batch_passed(resp.get_json()['id'])

    resp = client.post('/api/bom/calculate', json={'productCode': 'SP-QC-SUFFICIENT', 'quantity': 5})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert 'blockedMaterials' not in data
    assert len(data['lines']) == 1
    line = data['lines'][0]
    assert line['code'] == 'NVL-003'
    assert line['qty'] == round(2 * 5, 2)
    assert line['lineCost'] == round(2 * 5 * 500)
    assert data['totalCost'] == line['lineCost']


def test_bom_calculate_qc_gating_soft_deleted_consistency(logged_in_client):
    client = logged_in_client

    resp = client.put('/api/bom/SP-QC-SOFTDEL', json={
        'lines': [
            {'code': 'NVL-004', 'name': 'Nhan mac', 'unit': 'cái', 'unitCost': 1200, 'qtyPerUnit': 1},
        ],
    })
    assert resp.status_code == 200

    resp = client.post('/api/material-batches', json={'materialCode': 'NVL-004', 'quantity': 20})
    assert resp.status_code == 200
    batch_id = resp.get_json()['id']
    _mark_batch_passed(batch_id)

    # Currently sufficient (passed + enough qty) -> not blocked.
    resp = client.post('/api/bom/calculate', json={'productCode': 'SP-QC-SOFTDEL', 'quantity': 3})
    assert resp.status_code == 200
    assert 'blockedMaterials' not in resp.get_json()

    # Soft-delete the batch (it's the material's ONLY batch) -> total_batches
    # drops to 0 for this material, so the total_batches > 0 guard exempts
    # it as "never received", NOT as "received but insufficient" -- the
    # soft-deleted quantity must never leak into available_passed either
    # (Pitfall 4: both aggregates share one is_deleted = FALSE clause).
    resp = client.delete(f'/api/material-batches/{batch_id}')
    assert resp.status_code == 200

    resp = client.post('/api/bom/calculate', json={'productCode': 'SP-QC-SOFTDEL', 'quantity': 3})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert 'blockedMaterials' not in data
    assert len(data['lines']) == 1
    assert data['lines'][0]['code'] == 'NVL-004'
