import importlib.util
import logging
import sys
from io import BytesIO
from pathlib import Path
from types import ModuleType, SimpleNamespace

from flask import Flask

from core.services.dl_client import DLClient


ROOT = Path(__file__).resolve().parents[1]


class _FakeCv2:
    IMREAD_COLOR = 1

    @staticmethod
    def imdecode(_file_bytes, _flags):
        return object()


class _FakeNp:
    uint8 = object()

    @staticmethod
    def frombuffer(data, _dtype):
        return data


def _fake_logger_module():
    return SimpleNamespace(
        get_logger=lambda name: logging.getLogger(name),
        log_api_request=lambda *args, **kwargs: None,
    )


def _install_stub_package(monkeypatch, name):
    package = ModuleType(name)
    package.__path__ = []
    monkeypatch.setitem(sys.modules, name, package)
    return package


def _load_module(module_name, relative_path):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_model1_detect_returns_invoice_data_json(monkeypatch):
    invoice_payload = {
        "invoice_id": "INV_TEST",
        "date": "2026-06-14T00:00:00",
        "products": [
            {
                "product_id": "OCR_1",
                "product_name": "Milk",
                "quantity": 2,
                "unit_price": 10000,
                "line_total": 20000,
            }
        ],
        "total_amount": 20000,
        "detection_confidence": 0.91,
    }

    monkeypatch.setitem(sys.modules, "cv2", _FakeCv2)
    monkeypatch.setitem(sys.modules, "numpy", _FakeNp)
    _install_stub_package(monkeypatch, "services")
    _install_stub_package(monkeypatch, "utils")
    monkeypatch.setitem(
        sys.modules,
        "services.invoice_service",
        SimpleNamespace(
            process_invoice_image=lambda _image: invoice_payload,
            format_invoice_response=lambda data: {
                "success": True,
                "invoice_data": data,
                "data": data,
            },
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "config",
        SimpleNamespace(ALLOWED_EXTENSIONS={"png", "jpg", "jpeg"}, UPLOAD_DIR="uploads"),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.validators",
        SimpleNamespace(
            ValidationError=ValueError,
            validate_image_file=lambda _file: True,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "utils.database",
        SimpleNamespace(save_invoice_to_db=lambda _data: None),
    )
    monkeypatch.setitem(sys.modules, "utils.logger", _fake_logger_module())

    model1_routes = _load_module("test_model1_routes", "dl_service/api/model1_routes.py")
    app = Flask(__name__)
    app.register_blueprint(model1_routes.model1_bp)
    client = app.test_client()

    response = client.post(
        "/api/model1/detect",
        data={"file": (BytesIO(b"fake image bytes"), "invoice.png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True
    assert body["invoice_data"]["invoice_id"] == "INV_TEST"
    assert body["invoice_data"]["products"][0]["product_name"] == "Milk"


def test_model2_forecast_accepts_nested_ocr_invoice_data(monkeypatch):
    forecast_result = {
        "success": True,
        "predicted_quantity": 5,
        "predicted_products": [{"product_name": "Milk", "predicted_quantity": 5}],
        "trend": "stable",
        "confidence": 0.8,
    }
    captured = {}

    def fake_forecast(_model, items):
        captured["items"] = items
        return forecast_result

    _install_stub_package(monkeypatch, "services")
    _install_stub_package(monkeypatch, "utils")
    monkeypatch.setitem(
        sys.modules,
        "services.model_loader",
        SimpleNamespace(get_lstm_model=lambda: object()),
    )
    monkeypatch.setitem(
        sys.modules,
        "services.forecast_service",
        SimpleNamespace(
            parse_manual_invoice_data=lambda _data: [],
            forecast_quantity=fake_forecast,
            format_forecast_response=lambda result: result,
        ),
    )
    monkeypatch.setitem(sys.modules, "services.invoice_service", SimpleNamespace(invoice_history=[]))
    monkeypatch.setitem(
        sys.modules,
        "utils.validators",
        SimpleNamespace(ValidationError=ValueError, validate_invoice_data=lambda _data: True),
    )
    monkeypatch.setitem(sys.modules, "utils.database", SimpleNamespace(save_forecast_to_db=lambda _data: None))
    monkeypatch.setitem(sys.modules, "utils.logger", _fake_logger_module())

    model2_routes = _load_module("test_model2_routes", "dl_service/api/model2_routes.py")
    app = Flask(__name__)
    app.register_blueprint(model2_routes.model2_bp)
    client = app.test_client()

    response = client.post(
        "/api/model2/forecast",
        json={
            "invoice_data": {
                "products": [
                    {"product_name": "Milk", "quantity": 2, "unit_price": 10000},
                ],
            },
        },
    )

    assert response.status_code == 200
    assert captured["items"][0]["product_name"] == "Milk"
    assert response.get_json()["predicted_quantity"] == 5


def test_dl_client_normalizes_ocr_output_for_forecast():
    client = DLClient()

    payload = client._forecast_payload(
        {
            "invoice_data": {
                "products": [
                    {"product_name": "Milk", "quantity": 2},
                ],
            },
        }
    )

    assert payload["products"][0]["product_name"] == "Milk"
