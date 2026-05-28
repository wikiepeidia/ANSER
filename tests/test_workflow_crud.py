"""Integration tests for WorkflowRepo + workflow_service using SQLite in-memory."""
import sqlite3
import json

import pytest

from core.db.workflow_repo import WorkflowRepo
import core.services.workflow_service as workflow_service
from core.services.service_errors import ServiceValidationError


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def conn():
    """In-memory SQLite connection with workflows table."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("""
        CREATE TABLE workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            description TEXT,
            data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.commit()
    return c


@pytest.fixture()
def repo(conn):
    return WorkflowRepo(conn)


# ── WorkflowRepo direct ───────────────────────────────────────────────────────

def test_create_and_get_scenario(repo):
    sid = repo.create_scenario(1, "My Flow", "desc", True, '{"nodes":[]}')
    result = repo.get_scenario(sid, 1)
    assert result is not None
    assert result["name"] == "My Flow"
    assert result["description"] == "desc"


def test_get_scenario_wrong_user_returns_none(repo):
    sid = repo.create_scenario(1, "Flow", "d", False, "{}")
    assert repo.get_scenario(sid, user_id=999) is None


def test_list_scenarios_for_user(repo):
    repo.create_scenario(1, "A", "", False, "{}")
    repo.create_scenario(1, "B", "", False, "{}")
    repo.create_scenario(2, "C", "", False, "{}")
    results = repo.get_scenarios(user_id=1)
    assert len(results) == 2


def test_update_scenario_name(repo):
    sid = repo.create_scenario(1, "Old Name", "", False, "{}")
    repo.update_scenario(sid, 1, {"name": "New Name"})
    assert repo.get_scenario(sid, 1)["name"] == "New Name"


def test_update_scenario_steps(repo):
    sid = repo.create_scenario(1, "Flow", "", False, '{"nodes":[]}')
    repo.update_scenario(sid, 1, {"steps": '{"nodes":[1,2]}'})
    assert repo.get_scenario(sid, 1)["data"] == '{"nodes":[1,2]}'


def test_update_scenario_empty_payload_is_noop(repo):
    sid = repo.create_scenario(1, "Stable", "", False, "{}")
    repo.update_scenario(sid, 1, {})
    assert repo.get_scenario(sid, 1)["name"] == "Stable"


def test_delete_scenario_removes_it(repo):
    sid = repo.create_scenario(1, "ToDelete", "", False, "{}")
    repo.delete_scenario(sid, 1)
    assert repo.get_scenario(sid, 1) is None


def test_create_workflow(repo):
    wid = repo.create_workflow(1, "Workflow A", '{"nodes":[]}')
    assert isinstance(wid, int)
    assert wid > 0


# ── workflow_service layer ────────────────────────────────────────────────────

class _Conn:
    """Thin wrapper connecting workflow_service to our in-memory conn."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return self._conn.cursor()

    def commit(self):
        self._conn.commit()


def _make_conn(conn):
    return _Conn(conn)


def test_service_list_workflows_empty(conn):
    results = workflow_service.list_workflows_for_user(conn, user_id=1)
    assert results == []


def test_service_save_and_list_workflow(conn):
    result = workflow_service.save_workflow_for_user(
        conn, user_id=5,
        payload={"name": "Sales Flow", "data": {"nodes": []}},
    )
    assert result["message"] == "Workflow saved successfully"
    wid = result["id"]
    assert wid > 0

    workflows = workflow_service.list_workflows_for_user(conn, user_id=5)
    assert len(workflows) == 1
    assert workflows[0]["name"] == "Sales Flow"


def test_service_update_existing_workflow(conn):
    created = workflow_service.save_workflow_for_user(
        conn, user_id=7,
        payload={"name": "Old", "data": {}},
    )
    workflow_service.save_workflow_for_user(
        conn, user_id=7,
        payload={"id": created["id"], "name": "Updated", "data": {"k": "v"}},
    )
    workflows = workflow_service.list_workflows_for_user(conn, user_id=7)
    assert workflows[0]["name"] == "Updated"


def test_service_delete_workflow(conn):
    created = workflow_service.save_workflow_for_user(
        conn, user_id=9, payload={"name": "Temp", "data": {}},
    )
    workflow_service.delete_workflow_for_user(conn, user_id=9, workflow_id=created["id"])
    assert workflow_service.list_workflows_for_user(conn, user_id=9) == []


def test_service_get_workflow(conn):
    created = workflow_service.save_workflow_for_user(
        conn, user_id=11,
        payload={"name": "Detail", "data": {"nodes": [1]}},
    )
    wf = workflow_service.get_workflow_for_user(conn, user_id=11, workflow_id=created["id"])
    assert wf is not None
    assert wf["name"] == "Detail"
    assert wf["data"] == {"nodes": [1]}


def test_service_get_workflow_wrong_user_returns_none(conn):
    created = workflow_service.save_workflow_for_user(
        conn, user_id=13, payload={"name": "X", "data": {}},
    )
    result = workflow_service.get_workflow_for_user(conn, user_id=999, workflow_id=created["id"])
    assert result is None


def test_service_invalid_user_id_raises(conn):
    with pytest.raises(ServiceValidationError):
        workflow_service.list_workflows_for_user(conn, user_id=None)
