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


def test_sales_routes_remain_registered_after_extraction(app):
    route_map = _route_method_map(app)

    expected_routes = {
        "/sale": {"GET"},
        "/api/products/search": {"GET"},
        "/api/sales/create": {"POST"},
        "/api/sales/history": {"GET"},
        "/api/sales/history/<int:sale_id>": {"DELETE"},
    }

    for path, expected_methods in expected_routes.items():
        assert path in route_map, f"Missing extracted sales route: {path}"
        assert expected_methods.issubset(route_map[path])


def test_workspace_routes_remain_registered_after_extraction(app):
    route_map = _route_method_map(app)

    expected_routes = {
        "/api/workspaces": {"GET"},
        "/api/workspace/<int:workspace_id>/items": {"GET", "POST"},
        "/api/workspace": {"POST"},
        "/api/items/<int:item_id>": {"PUT", "DELETE"},
        "/api/scenarios": {"GET", "POST"},
        "/api/scenarios/<int:scenario_id>": {"GET", "PUT", "DELETE"},
    }

    for path, expected_methods in expected_routes.items():
        assert path in route_map, f"Missing extracted workspace/scenario route: {path}"
        assert expected_methods.issubset(route_map[path])


def test_admin_user_routes_remain_registered_after_extraction(app):
    route_map = _route_method_map(app)

    expected_routes = {
        "/api/admin/users": {"GET"},
        "/api/admin/activity": {"GET"},
        "/api/admin/stats": {"GET"},
        "/api/admin/create-manager": {"POST"},
        "/api/create-user": {"POST"},
        "/api/users": {"GET"},
        "/api/users/<int:user_id>": {"DELETE"},
        "/api/users/<int:user_id>/reset-password": {"POST"},
        "/api/admin/users/<int:user_id>": {"DELETE"},
        "/api/admin/users/promote": {"POST"},
        "/api/admin/users/demote": {"POST"},
        "/api/manager/users-permissions": {"GET"},
    }

    for path, expected_methods in expected_routes.items():
        assert path in route_map, f"Missing extracted admin/user route: {path}"
        assert expected_methods.issubset(route_map[path])


def test_analytics_dashboard_reports_automations_routes_remain_registered_after_extraction(app):
    route_map = _route_method_map(app)

    expected_routes = {
        "/api/admin/analytics/data": {"GET"},
        "/api/admin/analytics/clear_cache": {"POST"},
        "/api/dashboard/stats": {"GET"},
        "/api/reports/stats": {"GET"},
        "/api/reports/scheduled": {"GET", "POST"},
        "/api/reports/scheduled/<int:report_id>": {"DELETE"},
        "/api/automations": {"GET", "POST"},
        "/api/automations/<int:automation_id>": {"PUT", "DELETE"},
    }

    for path, expected_methods in expected_routes.items():
        assert path in route_map, f"Missing extracted operations route: {path}"
        assert expected_methods.issubset(route_map[path])


def test_admin_subscription_routes_remain_registered_after_extraction(app):
    route_map = _route_method_map(app)

    expected_routes = {
        "/api/admin/subscriptions": {"GET"},
        "/api/admin/subscription/auto-renew": {"POST"},
        "/api/admin/subscription/extend": {"POST"},
        "/api/admin/subscription-history": {"GET"},
        "/api/admin/extend-subscription": {"POST"},
        "/api/admin/check-expired-subscriptions": {"POST"},
    }

    for path, expected_methods in expected_routes.items():
        assert path in route_map, f"Missing extracted admin subscription route: {path}"
        assert expected_methods.issubset(route_map[path])


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
