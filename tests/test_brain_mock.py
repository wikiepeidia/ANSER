"""Covers N8N-02: routes/n8n_api.py's 3 Brain AI/OCR internal endpoints
(/api/n8n/internal/brain/chat, /upload, /mcp/validate-invoice) rewritten
from hardcoded always-succeeds stubs into a realistic mock that validates
input shape, can genuinely fail, and returns varied deterministic-per-input
responses instead of one static canned blob. See 05-CONTEXT.md's locked
"realistic mock" decision.

Uses the module-scoped `client` fixture (no login) — these endpoints are
called by n8n, which carries no Flask-Login session (see tests/conftest.py),
matching the identical pattern already used in tests/test_n8n_internal.py.
"""
from routes.inventory_routes import MATERIALS_CATALOG

_CATALOG_CODES = {m['code'] for m in MATERIALS_CATALOG}


# ── /chat ─────────────────────────────────────────────────────────────────

def test_chat_missing_prompt(client):
    resp = client.post('/api/n8n/internal/brain/chat', json={})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body['success'] is False
    assert body['mock'] is True


def test_chat_generic_prompt(client):
    resp = client.post('/api/n8n/internal/brain/chat', json={
        'route': 'GENERAL', 'prompt': 'Tóm tắt báo cáo doanh thu',
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['mock'] is True
    assert body['route'] == 'GENERAL'
    assert isinstance(body['text'], str) and body['text']


def test_chat_infer_production(client):
    resp = client.post('/api/n8n/internal/brain/chat', json={
        'route': 'TECHNICAL', 'prompt': 'x',
        'context': {'infer_production': {'items': [
            {'sku': 'NVL-001', 'qty': 10},
            {'sku': 'NVL-002', 'qty': 4},
        ]}},
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['inference']['items'] == [
        {'sku': 'NVL-001', 'qty_to_produce': 10},
        {'sku': 'NVL-002', 'qty_to_produce': 4},
    ]


# ── /mcp/validate-invoice ────────────────────────────────────────────────

def test_validate_invoice_missing_body(client):
    resp = client.post('/api/n8n/internal/brain/mcp/validate-invoice')
    assert resp.status_code == 400
    body = resp.get_json()
    assert body['success'] is False
    assert body['mock'] is True


def test_validate_invoice_match(client):
    resp = client.post('/api/n8n/internal/brain/mcp/validate-invoice', json={
        'items': [{'sku': 'NVL-001', 'qty': 10, 'unit_price': 45000}],
        'total': 450000,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['is_valid'] is True
    assert body['difference'] == 0
    assert body['ocr_total'] == 450000
    assert body['calculated_total'] == 450000


def test_validate_invoice_mismatch(client):
    resp = client.post('/api/n8n/internal/brain/mcp/validate-invoice', json={
        'items': [{'sku': 'NVL-001', 'qty': 10, 'unit_price': 45000}],
        'total': 500000,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['is_valid'] is False
    assert body['difference'] == 50000


def test_validate_invoice_empty_items(client):
    resp = client.post('/api/n8n/internal/brain/mcp/validate-invoice', json={
        'items': [], 'total': 0,
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['is_valid'] is False
    assert body['calculated_total'] == 0


# ── /upload (OCR) ────────────────────────────────────────────────────────

def test_upload_missing_scenario(client):
    resp = client.post('/api/n8n/internal/brain/upload')
    assert resp.status_code == 400
    body = resp.get_json()
    assert body['success'] is False
    assert body['mock'] is True


def test_upload_deterministic_and_valid_items(client):
    resp1 = client.post('/api/n8n/internal/brain/upload?scenario=weigh-slip-001')
    resp2 = client.post('/api/n8n/internal/brain/upload?scenario=weigh-slip-001')
    assert resp1.status_code == 200
    body1 = resp1.get_json()
    body2 = resp2.get_json()
    assert body1 == body2
    assert body1['mock'] is True
    items = body1['items']
    assert len(items) >= 1
    for item in items:
        assert item['sku'] in _CATALOG_CODES
        assert item['qty'] > 0
        assert item['unit_price'] > 0
    assert body1['total'] == round(sum(i['qty'] * i['unit_price'] for i in items))
    assert 0 < body1['confidence'] <= 1


def test_upload_varies_by_scenario(client):
    respA = client.post('/api/n8n/internal/brain/upload?scenario=weigh-slip-AAA')
    respB = client.post('/api/n8n/internal/brain/upload?scenario=weigh-slip-BBB')
    bodyA = respA.get_json()
    bodyB = respB.get_json()
    assert bodyA['items'] != bodyB['items'] or bodyA['confidence'] != bodyB['confidence']


def test_upload_low_quality_scenario(client):
    resp = client.post('/api/n8n/internal/brain/upload?scenario=blurry-weigh-slip')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['items'] == []
    assert body['confidence'] < 0.3


def test_upload_then_validate_invoice_round_trip(client):
    resp = client.post('/api/n8n/internal/brain/upload?scenario=round-trip-check')
    ocr = resp.get_json()

    resp2 = client.post('/api/n8n/internal/brain/mcp/validate-invoice', json={
        'items': ocr['items'], 'total': ocr['total'],
    })
    body2 = resp2.get_json()
    assert body2['is_valid'] is True
    assert body2['difference'] == 0
    assert body2['calculated_total'] == ocr['total']
