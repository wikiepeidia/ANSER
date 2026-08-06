"""Regression tests for the manufacturing VLM prompt and raw-output contract."""

import asyncio
import json
import sys
import types

import pytest


# The Windows authoring environment intentionally does not install the full
# Colab inference stack.  VisionAgent only needs json_repair at import time;
# these tests use valid JSON seeds, so stdlib json is an exact test double for
# that narrow input class when the real package is absent.
try:
    import json_repair  # noqa: F401
except ModuleNotFoundError:
    _json_repair_stub = types.ModuleType("json_repair")

    def _repair_json(raw, return_objects=False):
        parsed = json.loads(raw)
        return parsed if return_objects else json.dumps(parsed)

    _json_repair_stub.repair_json = _repair_json
    sys.modules["json_repair"] = _json_repair_stub

from src.agents.vision import VisionAgent  # noqa: E402


class _RawVisionEngine:
    def __init__(self, raw: str):
        self.raw = raw

    async def generate_vision(self, image_path, prompt, max_new_tokens=512):
        return self.raw


def _extract(raw: str) -> dict:
    agent = VisionAgent(_RawVisionEngine(raw))
    return asyncio.run(agent.extract_manufacturing_invoice("unused.png"))


def test_manufacturing_prompt_maps_visible_labels_without_null_value_example():
    prompt = VisionAgent.PROMPTS["manufacturing"]

    # A concrete JSON object with null values is an answer-shaped instance,
    # not a field/type contract.  The prompt must state types and mappings.
    assert '{"items":' not in prompt
    for label, target in (
        ("Số chứng từ", "doc_no"),
        ("So chung tu", "doc_no"),
        ("Mã khách hàng", "customer_code"),
        ("Ma Khach hang", "customer_code"),
        ("Khu vực giao", "region"),
        ("Khu vuc giao", "region"),
        ("Hạn giao", "deadline"),
        ("Han giao", "deadline"),
        ("Mã SKU sản phẩm", "items[].sku"),
        ("Ma SKU san pham", "items[].sku"),
    ):
        assert label in prompt
        assert target in prompt

    assert "DUY NHẤT một JSON hợp lệ" in prompt
    assert "KHÔNG suy đoán hay bịa" in prompt


@pytest.mark.parametrize(
    ("raw", "missing_key"),
    [
        ("{}", "items"),
        ('{"items": []}', "total"),
        ('{"total": 0}', "items"),
        ('{"farmer": "HTX A"}', "items"),
    ],
)
def test_manufacturing_parser_rejects_missing_core_keys(raw, missing_key):
    result = _extract(raw)

    assert "error" in result
    assert missing_key in result["error"]


def test_manufacturing_parser_accepts_explicit_honest_empty():
    result = _extract('{"items": [], "total": 0}')

    assert result == {"items": [], "total": 0}


def test_manufacturing_parser_accepts_valid_single_item():
    raw = json.dumps(
        {
            "items": [
                {
                    "sku": "SP-001",
                    "name": "Cao Atiso 100g",
                    "qty": 10,
                    "unit_price": 150000,
                }
            ],
            "total": 1650000,
            "doc_no": "DH-20260805-01",
            "customer_code": "KH-0088",
            "region": "Ha Noi",
            "deadline": "2026-08-15",
        }
    )

    result = _extract(raw)

    assert result["items"][0]["sku"] == "SP-001"
    assert result["doc_no"] == "DH-20260805-01"
