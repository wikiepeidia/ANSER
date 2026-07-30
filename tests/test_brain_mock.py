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
