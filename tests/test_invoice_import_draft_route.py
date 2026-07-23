"""Route-layer auth + end-to-end tests for
POST /api/n8n/internal/invoice-import-draft.
"""

from core.config import Config


_URL = '/api/n8n/internal/invoice-import-draft'
_TOKEN = 'test-shared-secret-token'


def _clean_payload(**overrides):
    payload = {
        "success": True,
        "needs_manual_review": False,
        "invoice": {
            "items": [{"name": "Coca Cola", "price": 12000, "qty": 5, "is_reduced_vat": True}],
            "total": 60000,
        },
    }
    payload.update(overrides)
    return payload


def _install_sqlite_db(app, sqlite_db):
    app.extensions['database'] = sqlite_db


def test_missing_token_rejected_with_401(app, client, sqlite_db, monkeypatch):
    monkeypatch.setattr(Config, 'ANSER_N8N_INTERNAL_TOKEN', _TOKEN)
    _install_sqlite_db(app, sqlite_db)

    resp = client.post(_URL, json=_clean_payload())

    assert resp.status_code == 401
    assert resp.get_json()['success'] is False

    conn = sqlite_db.get_business_connection()
    count = conn.execute('SELECT COUNT(*) AS cnt FROM import_transactions').fetchone()['cnt']
    conn.close()
    assert count == 0


def test_wrong_token_rejected_with_401(app, client, sqlite_db, monkeypatch):
    monkeypatch.setattr(Config, 'ANSER_N8N_INTERNAL_TOKEN', _TOKEN)
    _install_sqlite_db(app, sqlite_db)

    resp = client.post(_URL, json=_clean_payload(),
                        headers={'X-Webhook-Token': 'wrong-token'})

    assert resp.status_code == 401


def test_unset_expected_token_always_rejects_even_with_empty_header(app, client, sqlite_db, monkeypatch):
    monkeypatch.setattr(Config, 'ANSER_N8N_INTERNAL_TOKEN', '')
    _install_sqlite_db(app, sqlite_db)

    resp = client.post(_URL, json=_clean_payload(),
                        headers={'X-Webhook-Token': ''})

    assert resp.status_code == 401


def test_valid_token_and_clean_payload_creates_pending_review_draft(app, client, sqlite_db, monkeypatch):
    monkeypatch.setattr(Config, 'ANSER_N8N_INTERNAL_TOKEN', _TOKEN)
    _install_sqlite_db(app, sqlite_db)

    conn = sqlite_db.get_business_connection()
    conn.execute("INSERT INTO products (name, price, stock_quantity) VALUES ('Coca Cola', 12000, 10)")
    conn.commit()
    conn.close()

    resp = client.post(_URL, json=_clean_payload(),
                        headers={'X-Webhook-Token': _TOKEN})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body['success'] is True
    assert body['status'] == 'pending_review'
    assert body['matched_count'] == 1

    conn = sqlite_db.get_business_connection()
    row = conn.execute(
        "SELECT status FROM import_transactions WHERE id = ?", (body['id'],)
    ).fetchone()
    conn.close()
    assert row['status'] == 'pending_review'


def test_non_clean_payload_rejected_with_400(app, client, sqlite_db, monkeypatch):
    monkeypatch.setattr(Config, 'ANSER_N8N_INTERNAL_TOKEN', _TOKEN)
    _install_sqlite_db(app, sqlite_db)

    resp = client.post(_URL, json=_clean_payload(success=False),
                        headers={'X-Webhook-Token': _TOKEN})

    assert resp.status_code == 400
    assert resp.get_json()['success'] is False

    conn = sqlite_db.get_business_connection()
    count = conn.execute('SELECT COUNT(*) AS cnt FROM import_transactions').fetchone()['cnt']
    conn.close()
    assert count == 0
