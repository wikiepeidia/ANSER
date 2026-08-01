"""Integration tests for invoice/material Excel import and file attachments
(INVOICE-01, INVOICE-02) — routes/invoice_routes.py.
"""
import io

import openpyxl

from core.sanxuat_db import get_connection, now


def _build_invoice_workbook(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['Mã NVL', 'Số lượng', 'Nhà cung cấp'])
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def test_invoice_import_per_row_errors(logged_in_client):
    client = logged_in_client

    buffer = _build_invoice_workbook([
        ('NVL-001', 10, 'NCC Test Import'),
        ('', 5, ''),
        ('NVL-002', 3, ''),
    ])

    resp = client.post(
        '/api/invoices/import',
        data={'file': (buffer, 'test.xlsx')},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['importedCount'] == 2
    assert data['errorCount'] == 1
    assert data['errors'][0]['row'] == 3

    imported_ids = {entry['id'] for entry in data['imported']}

    resp = client.get('/api/material-batches')
    assert resp.status_code == 200
    batch_ids = {b['id'] for b in resp.get_json()['batches']}
    assert imported_ids.issubset(batch_ids)

    # Missing file -> 400, whole-file-level message.
    resp = client.post('/api/invoices/import', data={})
    assert resp.status_code == 400
    assert resp.get_json()['success'] is False


def test_invoice_attachment_upload_and_retrieve(logged_in_client):
    client = logged_in_client

    resp = client.post(
        '/api/invoices/attachments',
        data={
            'file': (io.BytesIO(b'%PDF-1.4 fake pdf bytes'), 'hoadon.pdf'),
            'refType': 'material_batch',
            'refId': '1',
        },
        content_type='multipart/form-data',
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    attachment_id = data['id']

    resp = client.get(f'/api/invoices/attachments/{attachment_id}')
    assert resp.status_code == 200
    assert resp.data == b'%PDF-1.4 fake pdf bytes'

    resp = client.get('/api/invoices/attachments?refType=material_batch&refId=1')
    assert resp.status_code == 200
    listed_ids = {a['id'] for a in resp.get_json()['attachments']}
    assert attachment_id in listed_ids

    resp = client.get('/api/invoices/attachments/999999')
    assert resp.status_code == 404


def test_invoice_attachment_rejects_bad_format_and_oversized(logged_in_client):
    client = logged_in_client

    def _count():
        resp = client.get('/api/invoices/attachments')
        return len(resp.get_json()['attachments'])

    before = _count()

    resp = client.post(
        '/api/invoices/attachments',
        data={'file': (io.BytesIO(b'not really an exe'), 'malware.exe')},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 400
    assert _count() == before

    resp = client.post(
        '/api/invoices/attachments',
        data={'file': (io.BytesIO(b'x' * (10 * 1024 * 1024 + 1)), 'toobig.pdf')},
        content_type='multipart/form-data',
    )
    assert resp.status_code == 400
    assert _count() == before
