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


def test_realistic_full_shape_brain_response_accepted_with_all_guarantees(app, client, sqlite_db, monkeypatch):
    """VER-01: the exact realistic Brain /ocr success shape (including the
    `backend` and `validation` fields Phase 2's existing 5 tests above never
    sent) is accepted by the real route + real service, produces a
    pending_review draft, preserves the unmatched item via raw_name, and
    leaves all pre-existing stock untouched.
    """
    monkeypatch.setattr(Config, 'ANSER_N8N_INTERNAL_TOKEN', _TOKEN)
    _install_sqlite_db(app, sqlite_db)

    conn = sqlite_db.get_business_connection()
    cur = conn.execute(
        "INSERT INTO products (name, price, stock_quantity) VALUES ('Bia Saigon Special', 15000, 50)"
    )
    baseline_product_id = cur.lastrowid
    conn.execute(
        "INSERT INTO warehouse_stock (warehouse_id, product_id, stock_quantity) VALUES (1, ?, 50)",
        (baseline_product_id,),
    )
    conn.commit()
    conn.close()

    realistic_payload = {
        "success": True,
        "backend": "qwen2-vl-2b",
        "invoice": {
            "items": [
                {"name": "Nước ngọt Coca 330ml", "price": 10000, "qty": 24, "is_reduced_vat": False}
            ],
            "total": 240000,
        },
        "validation": {"is_valid": True, "calculated_total": 240000, "difference": 0},
        "needs_manual_review": False,
    }

    resp = client.post(_URL, json=realistic_payload,
                        headers={'X-Webhook-Token': _TOKEN})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body['success'] is True
    assert body['status'] == 'pending_review'
    assert body['matched_count'] == 0
    assert body['unmatched_count'] == 1

    conn = sqlite_db.get_business_connection()
    tx_row = conn.execute(
        "SELECT status FROM import_transactions WHERE id = ?", (body['id'],)
    ).fetchone()
    assert tx_row['status'] == 'pending_review'

    detail_rows = conn.execute(
        "SELECT product_id, raw_name FROM import_details WHERE import_id = ?", (body['id'],)
    ).fetchall()
    assert len(detail_rows) == 1
    assert detail_rows[0]['product_id'] is None
    assert detail_rows[0]['raw_name'] == 'Nước ngọt Coca 330ml'

    product_count = conn.execute('SELECT COUNT(*) AS cnt FROM products').fetchone()['cnt']
    assert product_count == 1
    baseline_product = conn.execute(
        "SELECT stock_quantity FROM products WHERE id = ?", (baseline_product_id,)
    ).fetchone()
    assert baseline_product['stock_quantity'] == 50

    warehouse_stock_rows = conn.execute('SELECT stock_quantity FROM warehouse_stock').fetchall()
    conn.close()
    assert len(warehouse_stock_rows) == 1
    assert warehouse_stock_rows[0]['stock_quantity'] == 50
