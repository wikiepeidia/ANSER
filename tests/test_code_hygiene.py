import inspect
import sqlite3

from core import google_integration
from core.config import Config
from core.services.analytics_service import AnalyticsService
from core.utils import Utils


def test_analytics_service_uses_config_property_id(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "GA_PROPERTY_ID", "123456789")

    service = AnalyticsService()
    service.credentials_path = str(tmp_path / "analytics_service_account.json")

    assert service.property_id == "123456789"
    assert service.get_report()["source"] == "mock"


def test_analytics_service_has_no_print_calls():
    source = inspect.getsource(__import__("core.services.analytics_service", fromlist=[""]))

    assert "print(" not in source
    assert source.count("On failure, return mock data") == 1


def test_google_drive_query_escapes_single_quotes(monkeypatch):
    captured = {}

    class _Files:
        def list(self, **kwargs):
            captured["q"] = kwargs["q"]
            return self

        def execute(self):
            return {"files": [], "nextPageToken": None}

    class _Service:
        def files(self):
            return _Files()

    monkeypatch.setattr(google_integration, "get_google_service", lambda *_args, **_kwargs: _Service())

    result = google_integration.list_files(query_text="Bob's invoice")

    assert result == {"files": [], "nextPageToken": None}
    assert "name contains 'Bob\\'s invoice'" in captured["q"]


def test_format_workspace_tree_uses_named_fields_for_rows():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE workspaces (
           id INTEGER,
           user_id INTEGER,
           name TEXT,
           type TEXT,
           description TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO workspaces VALUES (?, ?, ?, ?, ?)",
        (7, 1, "Ops", "team", "Operations workspace"),
    )
    row = conn.execute("SELECT * FROM workspaces").fetchone()

    tree = Utils.format_workspace_tree([row, {"id": 8, "name": "Personal", "type": "personal", "description": "Mine"}])

    assert tree["team"][0]["id"] == 7
    assert tree["team"][0]["name"] == "Ops"
    assert tree["personal"][0]["description"] == "Mine"


def test_format_workspace_tree_has_no_direct_tuple_indexing():
    source = inspect.getsource(Utils.format_workspace_tree)

    assert "workspace[3]" not in source
    assert "workspace[0]" not in source
    assert "workspace[2]" not in source
    assert "workspace[4]" not in source
