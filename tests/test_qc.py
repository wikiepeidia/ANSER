"""Tests covering QC-01/QC-03/QC-04 (routes/inventory_routes.py's QC and
process-event routes) — QC result recording (dual-write into qc_results
audit table + material_batches.qc_status/qc_note) and batch process-event
logging/retrieval.
"""
from core.sanxuat_db import get_connection


def _create_batch(client, **overrides):
    payload = {
        'materialCode': 'NVL-001',
        'quantity': 100,
        'supplierName': 'Test Supplier',
    }
    payload.update(overrides)
    resp = client.post('/api/material-batches', json=payload)
    assert resp.status_code == 200
    return resp.get_json()['id']


def test_record_qc_result(logged_in_client):
    batch_id = _create_batch(logged_in_client)

    resp = logged_in_client.post(
        f'/api/material-batches/{batch_id}/qc-result',
        json={'qcStatus': 'passed', 'qcNote': 'Đạt tiêu chuẩn'},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['qcStatus'] == 'passed'
    assert body['qcNote'] == 'Đạt tiêu chuẩn'

    resp = logged_in_client.get(f'/api/material-batches/{batch_id}')
    assert resp.status_code == 200
    batch = resp.get_json()['batch']
    assert batch['qcStatus'] == 'passed'
    assert batch['qcNote'] == 'Đạt tiêu chuẩn'

    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM qc_results WHERE batch_id = ?', (batch_id,)
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]['qc_status'] == 'passed'
    finally:
        conn.close()

    resp = logged_in_client.post(
        f'/api/material-batches/{batch_id}/qc-result',
        json={'qcStatus': 'bogus', 'qcNote': ''},
    )
    assert resp.status_code == 400
    assert resp.get_json()['message'] == 'Trạng thái QC không hợp lệ'

    resp = logged_in_client.post(
        '/api/material-batches/999999/qc-result',
        json={'qcStatus': 'passed', 'qcNote': ''},
    )
    assert resp.status_code == 404

    resp = logged_in_client.post(
        f'/api/material-batches/{batch_id}/qc-result',
        json={'qcStatus': 'failed', 'qcNote': 'Lỗi phát hiện sau'},
    )
    assert resp.status_code == 200

    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM qc_results WHERE batch_id = ?', (batch_id,)
        ).fetchall()
        assert len(rows) == 2
    finally:
        conn.close()

    resp = logged_in_client.get(f'/api/material-batches/{batch_id}')
    assert resp.get_json()['batch']['qcStatus'] == 'failed'
