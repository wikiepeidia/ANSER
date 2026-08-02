from fastapi.testclient import TestClient

from src.api.main import app
import src.api.dependencies as deps

client = TestClient(app)


class _FakeVision:
    """Fake runtime.vision exposing only extract_manufacturing_invoice, matching
    test_server_basics.py's monkeypatch.setattr(deps, ...) convention."""

    def __init__(self, extraction: dict):
        self._extraction = extraction

    async def extract_manufacturing_invoice(self, path: str) -> dict:
        return self._extraction


async def _noop_ensure_vision_runtime():
    return None


def _patch_vision(monkeypatch, extraction: dict):
    monkeypatch.setattr(deps.runtime, "ensure_vision_runtime", _noop_ensure_vision_runtime)
    monkeypatch.setattr(deps.runtime, "vision", _FakeVision(extraction))


def _post_manufacturing_ocr():
    return client.post(
        "/ocr/manufacturing",
        files={"file": ("test.png", b"fake-bytes", "image/png")},
    )


def test_manufacturing_ocr_happy_path_returns_all_fields(monkeypatch):
    # qty=10, unit_price=1000 -> base=10000, VAT 10% = 1000 -> line total 11000
    # total (VAT-inclusive) matches MCPServer's deterministic recompute exactly.
    extraction = {
        "items": [{"sku": "NL-001", "name": "Lá dược liệu", "qty": 10, "unit_price": 1000}],
        "total": 11000,
        "farmer": "HTX Nông sản Sạch Đà Lạt",
        "region_grown": "Đà Lạt",
        "part": "lá",
        "form": "tuoi",
        "gacp_cert": "GACP-1234",
        "doc_no": "DH-0001",
        "customer_code": "KH-001",
        "region": "HN",
        "deadline": "2026-09-01",
    }
    _patch_vision(monkeypatch, extraction)

    response = _post_manufacturing_ocr()

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["needs_manual_review"] is False

    invoice = payload["invoice"]
    for field in (
        "items", "total", "farmer", "region_grown", "part", "form",
        "gacp_cert", "doc_no", "customer_code", "region", "deadline",
    ):
        assert field in invoice
    assert invoice["items"][0]["sku"] == "NL-001"
    assert invoice["items"][0]["name"] == "Lá dược liệu"
    assert invoice["items"][0]["qty"] == 10
    assert invoice["items"][0]["unit_price"] == 1000
