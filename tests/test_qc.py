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
        assert rows[0]['result'] == 'pass'
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


def test_log_batch_event(logged_in_client):
    batch_id = _create_batch(logged_in_client)

    resp = logged_in_client.post(
        f'/api/material-batches/{batch_id}/events',
        json={'event': 'Bắt đầu sản xuất', 'note': 'Ca sáng'},
    )
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True

    # Novel event string not in the mock's 5-name vocabulary — no enum
    # restriction, matching the mock's own unvalidated addProcessEvent.
    resp = logged_in_client.post(
        f'/api/material-batches/{batch_id}/events',
        json={'event': 'Kiểm tra đột xuất'},
    )
    assert resp.status_code == 200

    resp = logged_in_client.post(
        f'/api/material-batches/{batch_id}/events',
        json={'event': ''},
    )
    assert resp.status_code == 400

    resp = logged_in_client.post(
        '/api/material-batches/999999/events',
        json={'event': 'Bắt đầu sản xuất'},
    )
    assert resp.status_code == 404
    assert resp.get_json()['message'] == 'Không tìm thấy lô nguyên liệu'


def test_get_batch_events(logged_in_client):
    batch_id = _create_batch(logged_in_client)

    events = ['Bắt đầu sản xuất', 'Dừng sản xuất', 'Tiếp tục sản xuất']
    for event in events:
        resp = logged_in_client.post(
            f'/api/material-batches/{batch_id}/events',
            json={'event': event},
        )
        assert resp.status_code == 200

    resp = logged_in_client.get(f'/api/material-batches/{batch_id}/events')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['success'] is True
    returned_events = body['events']
    assert len(returned_events) == 3
    assert [e['event'] for e in returned_events] == events
    for e in returned_events:
        assert e['batchId'] == batch_id
        assert e['ts']

    other_batch_id = _create_batch(logged_in_client)
    resp = logged_in_client.post(
        f'/api/material-batches/{other_batch_id}/events',
        json={'event': 'Hoàn thành'},
    )
    assert resp.status_code == 200

    resp = logged_in_client.get(f'/api/material-batches/{batch_id}/events')
    assert len(resp.get_json()['events']) == 3
