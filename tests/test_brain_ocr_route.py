"""Unit + route-layer tests for POST /api/brain/ocr and _wrap_brain_result()."""

from routes.dl_routes import _wrap_brain_result


def test_wrap_brain_result_success_shape():
    brain_result = {
        "success": True,
        "backend": "vlm-1",
        "invoice": {"items": [{"name": "Coca Cola", "price": 12000, "qty": 5}], "total": 60000},
        "needs_manual_review": False,
    }

    payload, status = _wrap_brain_result(brain_result)

    assert status == 200
    assert payload == {"success": True, "data": brain_result}


def test_wrap_brain_result_business_logic_failure_shape():
    brain_result = {
        "success": False,
        "backend": "vlm-1",
        "error": "VLM extraction failed",
        "raw": "...",
    }

    payload, status = _wrap_brain_result(brain_result)

    assert status == 500
    assert payload == {"success": False, "error": "VLM extraction failed"}


def test_wrap_brain_result_connection_failure_shape():
    brain_result = {"error": "Brain unreachable"}

    payload, status = _wrap_brain_result(brain_result)

    assert status == 500
    assert payload == {"success": False, "error": "Brain unreachable"}


def test_unauthenticated_post_rejected_with_401(client):
    resp = client.post('/api/brain/ocr', data={}, content_type='multipart/form-data')

    assert resp.status_code == 401
    assert resp.get_json()['success'] is False
