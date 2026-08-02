from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_validate_invoice_valid_match_returns_is_valid_true():
    # qty=10, unit_price=1000 -> base 10000, VAT 10% = 1000 -> line total
    # 11000, matching the stated total exactly.
    response = client.post(
        "/mcp/validate-invoice",
        json={
            "items": [{"sku": "NL-001", "name": "Lá dược liệu", "qty": 10, "unit_price": 1000}],
            "total": 11000,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["validation"]["is_valid"] is True
    assert payload["validation"]["calculated_total"] == 11000
    assert payload["validation"]["stated_total"] == 11000
    assert payload["validation"]["difference"] == 0
    assert payload["needs_manual_review"] is False
