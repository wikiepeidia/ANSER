import json
from pathlib import Path

MANIFEST_PATH = Path(
    ".planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json"
)


def _load_manifest():
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _route_method_map(app):
    route_map = {}
    for rule in app.url_map.iter_rules():
        methods = {m for m in rule.methods if m not in {"HEAD", "OPTIONS"}}
        if rule.rule not in route_map:
            route_map[rule.rule] = set()
        route_map[rule.rule].update(methods)
    return route_map


def test_manifest_has_core_endpoints():
    manifest = _load_manifest()
    paths = {entry["path"] for entry in manifest["endpoints"]}

    assert "/api/workflows" in paths
    assert "/api/workflow/execute" in paths
    assert "/api/ai/chat" in paths
    assert "/api/imports" in paths
    assert "/api/exports" in paths


def test_route_registry_contains_manifest_paths_and_methods(app):
    manifest = _load_manifest()
    route_map = _route_method_map(app)

    for entry in manifest["endpoints"]:
        path = entry["path"]
        expected_methods = set(entry.get("methods", []))

        assert path in route_map, f"Missing route path in app registry: {path}"
        assert expected_methods.issubset(
            route_map[path]
        ), f"Method mismatch for {path}: expected {sorted(expected_methods)} got {sorted(route_map[path])}"


def test_snapshot_file_has_required_schema():
    snapshot_path = Path(
        ".planning/phases/11-baseline-contract-guardrails/11-endpoint-snapshot.json"
    )
    assert snapshot_path.exists(), "Snapshot file should exist before contract test run"

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    entries = snapshot["snapshot"]["entries"]
    assert isinstance(entries, list) and entries, "Snapshot entries must be a non-empty list"

    first = entries[0]
    assert "path" in first
    assert "actual_methods" in first
