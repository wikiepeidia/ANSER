"""Unit tests for core.services.brain_client.BrainClient."""

import pytest
import requests

from core.config import Config
from core.services.brain_client import BrainClient


def test_unconfigured_brain_url_short_circuits_without_network_call(monkeypatch):
    monkeypatch.setattr(Config, 'BRAIN_URL', '')

    def fake_post(*args, **kwargs):
        raise AssertionError("requests.post should not be called when BRAIN_URL is unset")

    monkeypatch.setattr('core.services.brain_client.requests.post', fake_post)

    client = BrainClient()
    result = client.run_ocr(file_bytes=b'fake-bytes', filename='invoice.jpg')

    assert result == {"error": "BRAIN_URL is not configured"}


def test_connection_error_is_wrapped_as_error_dict(monkeypatch):
    monkeypatch.setattr(Config, 'BRAIN_URL', 'https://brain.example.com')
    monkeypatch.setattr(Config, 'BRAIN_TOKEN', 'test-token')

    def fake_post(*args, **kwargs):
        raise requests.exceptions.ConnectionError("Brain unreachable")

    monkeypatch.setattr('core.services.brain_client.requests.post', fake_post)

    client = BrainClient()
    result = client.run_ocr(file_bytes=b'fake-bytes', filename='invoice.jpg')

    assert result == {"error": "Brain unreachable"}


def test_success_response_returned_unchanged_with_expected_headers(monkeypatch):
    monkeypatch.setattr(Config, 'BRAIN_URL', 'https://brain.example.com')
    monkeypatch.setattr(Config, 'BRAIN_TOKEN', 'test-token')

    brain_success_shape = {
        "success": True,
        "backend": "vlm-1",
        "invoice": {"items": [{"name": "Coca Cola", "price": 12000, "qty": 5}], "total": 60000},
        "validation": {"is_valid": True},
        "needs_manual_review": False,
    }

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return brain_success_shape

    def fake_post(url, files=None, headers=None, timeout=None):
        captured['url'] = url
        captured['files'] = files
        captured['headers'] = headers
        captured['timeout'] = timeout
        return FakeResponse()

    monkeypatch.setattr('core.services.brain_client.requests.post', fake_post)

    client = BrainClient()
    result = client.run_ocr(file_bytes=b'fake-bytes', filename='invoice.jpg')

    assert result == brain_success_shape
    assert captured['url'] == 'https://brain.example.com/ocr'
    assert captured['headers']['X-API-Token'] == 'test-token'
    assert captured['headers']['ngrok-skip-browser-warning'] == 'true'
    assert 'file' in captured['files']
