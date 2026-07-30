"""Tests covering SEC-01 (role-gated sensitive actions).

`logged_in_client` (tests/conftest.py) is a manager-role session;
`regular_user_client` is a second, non-manager (role='user') session. Every
SEC-01 call site is proven both ways: manager gets through to route logic,
regular_user_client is blocked with the standard 403 body.
"""

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
