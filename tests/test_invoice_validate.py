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


def test_validate_invoice_genuine_mismatch_returns_is_valid_false_with_correct_difference():
    # Correct VAT-inclusive line total is 11000, but stated total is
    # deliberately wrong (100000) -- far outside MCPServer's tolerance.
    response = client.post(
        "/mcp/validate-invoice",
        json={
            "items": [{"sku": "NL-003", "name": "Hoa dược liệu", "qty": 10, "unit_price": 1000}],
            "total": 100000,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["validation"]["is_valid"] is False
    assert payload["validation"]["difference"] == 89000
    assert payload["needs_manual_review"] is True


def test_validate_invoice_missing_body_returns_400():
    response = client.post("/mcp/validate-invoice")

    assert response.status_code == 400


def test_validate_invoice_malformed_json_returns_400():
    response = client.post(
        "/mcp/validate-invoice",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400


def test_validate_invoice_empty_items_returns_honest_low_confidence_result():
    response = client.post(
        "/mcp/validate-invoice",
        json={"items": [], "total": 0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["validation"]["is_valid"] is True
    assert payload["needs_manual_review"] is True


def test_validate_invoice_adversarial_numeric_input_returns_400():
    response = client.post(
        "/mcp/validate-invoice",
        json={
            "items": [{"sku": "NL-999", "name": "X", "qty": 1, "unit_price": 1e300}],
            "total": 1000,
        },
    )

    assert response.status_code == 400
