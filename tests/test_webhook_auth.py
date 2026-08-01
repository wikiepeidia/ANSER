"""SEC-02 coverage: every /api/n8n/internal/* route must 401 without a
valid X-Anser-Token header and behave normally with the correct one.

Uses its OWN fresh, unmodified app.test_client() instance per test (not the
shared `client` fixture from conftest.py, which always carries a valid
token via environ_base) so these tests can genuinely omit/mismatch the
header.
"""
from core.config import Config


def test_internal_notify_401_without_token(app):
    fresh_client = app.test_client()
    resp = fresh_client.post('/api/n8n/internal/notify', json={'msg': 'hi'})
    assert resp.status_code == 401
    assert resp.get_json() == {'success': False, 'error': 'unauthorized'}


def test_internal_notify_401_with_wrong_token(app):
    fresh_client = app.test_client()
    resp = fresh_client.post(
        '/api/n8n/internal/notify', json={'msg': 'hi'},
        headers={'X-Anser-Token': 'wrong-token'},
    )
    assert resp.status_code == 401


def test_internal_notify_200_with_correct_token(app):
    fresh_client = app.test_client()
    resp = fresh_client.post(
        '/api/n8n/internal/notify', json={'msg': 'hi'},
        headers={'X-Anser-Token': Config.ANSER_WEBHOOK_TOKEN},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['success'] is True
