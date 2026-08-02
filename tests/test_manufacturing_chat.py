import json

from fastapi.testclient import TestClient

from src.api.main import app
import src.api.dependencies as deps
import src.api.routes.chat as chat_mod
from src.core.engine import TASK_REGISTRY
from src.core.sanxuat_api import SanXuatAPI

client = TestClient(app)


class _FakeEngine:
    """Reimplements ModelEngine.background_worker's exact 3-branch logic so
    tests don't need a real ModelEngine (no GPU/vLLM)."""

    async def background_worker(self, task_id, handler_func, *args, **kwargs):
        TASK_REGISTRY.set(task_id, {"status": "running"})
        try:
            result = await handler_func(*args, **kwargs)
            TASK_REGISTRY.set(task_id, {"status": "completed", "result": result})
        except Exception as e:
            TASK_REGISTRY.set(task_id, {"status": "failed", "error": str(e)})


def _poll_task(client, task_id, max_retries=20):
    """Defensive polling loop -- background tasks complete synchronously
    within TestClient's request cycle (matches test_server.py's convention)."""
    last = None
    for _ in range(max_retries):
        status_resp = client.get(f"/api/v1/task/{task_id}")
        last = status_resp.json()
        if last["status"] in ("completed", "failed"):
            return last
    return last


class _FakeManager:
    """analyze_task always routes DATA_INTERNAL; answer_data captures the
    context it was called with so tests can assert on it."""

    async def analyze_task(self, msg):
        return {"category": "DATA_INTERNAL", "score": 1.0, "margin": 1.0, "method": "test"}

    async def answer_data(self, task, context=""):
        self.last_context = context
        return f"[FAKE TRẢ LỜI] {context[:80]}"


async def _noop_ensure_text_runtime():
    return None


def _patch_runtime_basics(monkeypatch, manager):
    monkeypatch.setattr(deps.runtime, "ensure_text_runtime", _noop_ensure_text_runtime)
    monkeypatch.setattr(deps.runtime, "manager", manager)
    monkeypatch.setattr(deps.runtime, "coder", object())
    monkeypatch.setattr(deps.runtime, "engine", _FakeEngine())


class _FakeSanXuatAPI:
    def lookup_production_order(self, query, limit=20):
        return json.dumps(
            [{
                "code": "DH-1001", "product_code": "SP-001",
                "product_name": "Cao dược liệu A", "quantity": 50,
                "unit": "hộp", "status": "in_progress",
            }],
            ensure_ascii=False,
        )

    def get_material_batch_status(self, query, limit=20):
        return json.dumps(
            [{
                "batch_code": "LO-2001", "material_code": "NL-001",
                "material_name": "Lá dược liệu", "quantity": 120,
                "import_date": "2026-07-01", "expiry_date": "2027-01-01",
                "qc_status": "passed",
            }],
            ensure_ascii=False,
        )


def test_manufacturing_chat_data_internal_dispatches_to_sanxuat_and_shapes_context(monkeypatch):
    manager = _FakeManager()
    _patch_runtime_basics(monkeypatch, manager)
    monkeypatch.setattr(chat_mod, "_sanxuat", _FakeSanXuatAPI())

    response = client.post(
        "/chat/manufacturing",
        json={"prompt": "lệnh sản xuất DH-1001 còn bao nhiêu"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "task_id" in body

    result_status = _poll_task(client, body["task_id"])
    assert result_status["status"] == "completed"

    result = result_status["result"]
    assert result["success"] is True
    assert result["mock"] is False
    assert result["route"] == "DATA_INTERNAL"
    assert "[FAKE TRẢ LỜI]" in result["text"]

    assert "DH-1001" in manager.last_context
    assert "LO-2001" in manager.last_context


def test_manufacturing_chat_survives_unreachable_db(monkeypatch):
    manager = _FakeManager()
    _patch_runtime_basics(monkeypatch, manager)

    monkeypatch.delenv("SANXUAT_POSTGRES_URL", raising=False)
    real_sanxuat = SanXuatAPI()
    assert real_sanxuat.engine is None

    monkeypatch.setattr(chat_mod, "_sanxuat", real_sanxuat)

    response = client.post(
        "/chat/manufacturing",
        json={"prompt": "kho nguyên liệu"},
    )
    assert response.status_code == 200
    body = response.json()

    result_status = _poll_task(client, body["task_id"])
    assert result_status["status"] == "completed"

    result = result_status["result"]
    assert result["success"] is True
    assert "không lấy được dữ liệu" in manager.last_context
