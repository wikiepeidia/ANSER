from fastapi.testclient import TestClient

from src.api.main import app
import src.api.dependencies as deps

client = TestClient(app)


def test_health_endpoint_returns_runtime_status():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert "status" in payload
    assert "runtime_profile" in payload
    assert "degraded" in payload


def test_chat_rejects_when_api_token_is_required(monkeypatch):
    monkeypatch.setattr(deps, "API_AUTH_TOKEN", "secret-token")
    response = client.post(
        "/chat",
        json={"user_id": 1, "store_id": 1, "message": "hello"},
    )
    assert response.status_code == 401
