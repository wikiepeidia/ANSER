"""Unit tests for workflow service delegation behavior."""

import core.services.workflow_service as workflow_service
from core.services.service_errors import ServiceValidationError


class _WorkflowCursor:
    def __init__(self, rows=None, lastrowid=0):
        self.rows = rows or []
        self.lastrowid = lastrowid
        self.executed = []

    def execute(self, query, params):
        self.executed.append((query, params))

    def fetchall(self):
        return self.rows


class _WorkflowConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1


def test_execute_user_workflow_parses_google_token_json(monkeypatch, workflow_payload):
    called = {}

    def _fake_execute(workflow_data, token_info):
        called["workflow_data"] = workflow_data
        called["token_info"] = token_info
        return {"status": "ok"}

    monkeypatch.setattr(workflow_service, "execute_workflow", _fake_execute)

    result = workflow_service.execute_user_workflow(
        workflow_payload,
        '{"access_token": "token-123"}',
    )

    assert result == {"status": "ok"}
    assert called["workflow_data"] == workflow_payload
    assert called["token_info"] == {"access_token": "token-123"}


def test_execute_user_workflow_rejects_invalid_payload():
    try:
        workflow_service.execute_user_workflow([], None)
        assert False, "Expected ServiceValidationError"
    except ServiceValidationError:
        pass


def test_list_workflows_for_user_serializes_data_field():
    rows = [
        (1, "Flow A", '{"nodes": []}', "2026-01-01", "2026-01-02"),
        (2, "Flow B", None, "2026-01-03", "2026-01-04"),
    ]
    conn = _WorkflowConn(_WorkflowCursor(rows=rows))

    workflows = workflow_service.list_workflows_for_user(conn, user_id=7)

    assert len(workflows) == 2
    assert workflows[0]["name"] == "Flow A"
    assert workflows[0]["data"] == {"nodes": []}
    assert workflows[1]["data"] == {}


def test_save_workflow_for_user_create_branch_commits_once():
    cursor = _WorkflowCursor(lastrowid=88)
    conn = _WorkflowConn(cursor)

    result = workflow_service.save_workflow_for_user(
        conn,
        user_id=5,
        payload={"name": "New Flow", "data": {"k": "v"}},
    )

    assert result["id"] == 88
    assert result["message"] == "Workflow saved successfully"
    assert any("INSERT INTO workflows" in entry[0] for entry in cursor.executed)
    assert conn.commits == 1


def test_save_workflow_for_user_update_branch_uses_existing_id():
    cursor = _WorkflowCursor(lastrowid=0)
    conn = _WorkflowConn(cursor)

    result = workflow_service.save_workflow_for_user(
        conn,
        user_id=12,
        payload={"id": 44, "name": "Updated", "data": {"nodes": [1]}},
    )

    assert result["id"] == 44
    assert any("UPDATE workflows SET name = ?" in entry[0] for entry in cursor.executed)
    assert conn.commits == 1
