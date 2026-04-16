import json
from pathlib import Path

import pytest

MANIFEST_PATH = Path(
    ".planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json"
)


def _load_manifest():
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _run_smoke_request(client, endpoint):
    smoke = endpoint.get("smoke")
    assert smoke is not None, f"Missing smoke config for endpoint: {endpoint['id']}"

    method = smoke.get("method", "GET")
    path = smoke.get("sample_path", endpoint["path"])
    expected_status = smoke.get("expected_status", [200, 204, 302, 401, 403, 404])

    response = client.open(path, method=method, follow_redirects=False)
    assert response.status_code in expected_status, (
        f"Unexpected status for {endpoint['id']} ({method} {path}). "
        f"Got {response.status_code}, expected one of {expected_status}."
    )

    if endpoint.get("response_keys_any") and response.is_json:
        payload = response.get_json(silent=True)
        assert isinstance(payload, dict)
        assert any(
            key in payload for key in endpoint["response_keys_any"]
        ), f"JSON payload for {endpoint['id']} missing expected keys"


@pytest.fixture(scope="module")
def manifest():
    return _load_manifest()


def _group_entries(manifest, group):
    return [
        entry
        for entry in manifest["endpoints"]
        if entry.get("group") == group and entry.get("smoke")
    ]


@pytest.mark.parametrize("group", ["workflow", "ai", "import_export"])
def test_group_smoke_statuses(client, manifest, group):
    entries = _group_entries(manifest, group)
    assert entries, f"Expected smoke entries for group: {group}"

    for entry in entries:
        _run_smoke_request(client, entry)


@pytest.mark.parametrize(
    "endpoint_id",
    ["page-home", "page-dashboard", "page-imports", "page-exports"],
)
def test_page_route_smoke_statuses(client, manifest, endpoint_id):
    entry = next(item for item in manifest["endpoints"] if item["id"] == endpoint_id)
    _run_smoke_request(client, entry)
