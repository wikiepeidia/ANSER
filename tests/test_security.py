"""Tests covering SEC-01 (role-gated sensitive actions).

`logged_in_client` (tests/conftest.py) is a manager-role session;
`regular_user_client` is a second, non-manager (role='user') session. Every
SEC-01 call site is proven both ways: manager gets through to route logic,
regular_user_client is blocked with the standard 403 body.
"""
from core.sanxuat_db import get_connection

FORBIDDEN_MESSAGE = 'Không đủ quyền truy cập'


def _create_product(client, code):
    resp = client.post('/api/products', json={
        'code': code, 'name': f'Sản phẩm bảo mật {code}', 'price': 10000,
    })
    assert resp.status_code == 200
    resp = client.get('/api/products')
    assert resp.status_code == 200
    for p in resp.get_json()['products']:
        if p['code'] == code:
            return p['id']
    raise AssertionError(f'product {code} not found after creation')


def _create_production_order(client, product_code):
    resp = client.post('/api/production-orders', json={
        'productCode': product_code,
        'productName': f'SP bảo mật {product_code}',
        'quantity': 5,
        'unit': 'cái',
        'customerName': 'Khách Test',
        'notes': '',
    })
    assert resp.status_code == 200
    return resp.get_json()['id']


def _create_material_batch(client, material_code='NVL-001'):
    resp = client.post('/api/material-batches', json={
        'materialCode': material_code, 'quantity': 50, 'supplierName': 'NCC Bảo Mật',
    })
    assert resp.status_code == 200
    return resp.get_json()['id']


def test_delete_product_requires_manager_role(logged_in_client, regular_user_client):
    # regular_user_client (role='user') is blocked with the standard message.
    product_id = _create_product(logged_in_client, 'SEC-DEL-1')
    resp = regular_user_client.delete(f'/api/products/{product_id}')
    assert resp.status_code == 403
    assert resp.get_json() == {'success': False, 'message': FORBIDDEN_MESSAGE}

    # logged_in_client (role='manager') is let through to the route logic
    # (not blocked by the role gate -- response is not 403).
    resp = logged_in_client.delete(f'/api/products/{product_id}')
    assert resp.status_code != 403
    assert resp.get_json()['success'] is True


def test_transition_approval_requires_manager_role(logged_in_client, regular_user_client):
    order_id = _create_production_order(logged_in_client, 'SEC-ORD-1')

    # Ungated edge: regular_user_client CAN move draft -> pending_approval
    # (the gate is scoped exactly to the approved edge, per 06-CONTEXT.md).
    resp = regular_user_client.post(
        f'/api/production-orders/{order_id}/transition', json={'status': 'pending_approval'})
    assert resp.status_code == 200

    # Gated edge: regular_user_client is blocked on pending_approval -> approved.
    resp = regular_user_client.post(
        f'/api/production-orders/{order_id}/transition', json={'status': 'approved'})
    assert resp.status_code == 403
    assert resp.get_json() == {'success': False, 'message': 'Không đủ quyền duyệt đơn hàng'}

    # No partial write happened on the blocked path -- status is unchanged.
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT status FROM production_orders WHERE id = ?', (order_id,)
        ).fetchone()
        assert row['status'] == 'pending_approval'
    finally:
        conn.close()

    # Manager succeeds on the same gated edge.
    resp = logged_in_client.post(
        f'/api/production-orders/{order_id}/transition', json={'status': 'approved'})
    assert resp.status_code == 200


def test_qc_result_requires_manager_role(logged_in_client, regular_user_client):
    batch_id = _create_material_batch(logged_in_client)

    resp = regular_user_client.post(
        f'/api/material-batches/{batch_id}/qc-result',
        json={'qcStatus': 'passed', 'qcNote': ''},
    )
    assert resp.status_code == 403
    assert resp.get_json() == {'success': False, 'message': FORBIDDEN_MESSAGE}

    resp = logged_in_client.post(
        f'/api/material-batches/{batch_id}/qc-result',
        json={'qcStatus': 'passed', 'qcNote': ''},
    )
    assert resp.status_code != 403
    assert resp.get_json()['success'] is True


def test_n8n_workflow_admin_requires_manager_role(logged_in_client, regular_user_client):
    # regular_user_client is blocked on both routes before any n8n network
    # call is attempted (the role-check decorator runs before the view body).
    resp = regular_user_client.delete('/api/n8n/workflows/999')
    assert resp.status_code == 403
    assert resp.get_json() == {'success': False, 'message': FORBIDDEN_MESSAGE}

    resp = regular_user_client.post('/api/n8n/templates/deploy', json={'slug': 'bogus'})
    assert resp.status_code == 403
    assert resp.get_json() == {'success': False, 'message': FORBIDDEN_MESSAGE}

    # Manager gets through the gate. This test environment has no live n8n
    # instance, so only "did the gate let it through" is asserted -- 502
    # ("Cannot reach n8n") / 404 ("Template not found") are both acceptable
    # non-403 outcomes, not a claim about downstream n8n integration.
    resp = logged_in_client.delete('/api/n8n/workflows/999')
    assert resp.status_code != 403

    resp = logged_in_client.post('/api/n8n/templates/deploy', json={'slug': 'bogus'})
    assert resp.status_code != 403
