"""Workflow service functions extracted from route handlers."""

import json

from core.workflow_engine import execute_workflow

from .service_errors import ServiceValidationError


def _decode_google_token(raw_token):
    """Decode persisted token payload into a dictionary when possible."""
    if not raw_token:
        return None
    if isinstance(raw_token, dict):
        return raw_token
    if isinstance(raw_token, str):
        try:
            return json.loads(raw_token)
        except Exception:
            return None
    return None


def execute_user_workflow(workflow_data, google_token_raw):
    """Execute workflow with token decoding delegated from the route layer."""
    if not isinstance(workflow_data, dict):
        raise ServiceValidationError("workflow_data must be a dictionary")

    token_info = _decode_google_token(google_token_raw)
    return execute_workflow(workflow_data, token_info)


def list_workflows_for_user(db_conn, user_id):
    """Return serialized workflow rows for a user."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT id, name, data, created_at, updated_at FROM workflows "
        "WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()

    workflows = []
    for row in rows:
        parsed = {}
        if row[2]:
            try:
                parsed = json.loads(row[2]) if isinstance(row[2], str) else row[2]
            except Exception:
                parsed = {}
        workflows.append(
            {
                "id": row[0],
                "name": row[1],
                "data": parsed,
                "created_at": row[3],
                "updated_at": row[4],
            }
        )
    return workflows


def save_workflow_for_user(db_conn, user_id, payload):
    """Create or update a workflow for a user."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")
    if not isinstance(payload, dict):
        raise ServiceValidationError("payload must be a dictionary")

    name = payload.get("name", "Untitled Workflow")
    workflow_data = json.dumps(payload.get("data", {}))
    workflow_id = payload.get("id")

    cursor = db_conn.cursor()
    if workflow_id:
        cursor.execute(
            "UPDATE workflows SET name = ?, data = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ? AND user_id = ?",
            (name, workflow_data, workflow_id, user_id),
        )
    else:
        cursor.execute(
            "INSERT INTO workflows (user_id, name, data) VALUES (?, ?, ?)",
            (user_id, name, workflow_data),
        )
        workflow_id = cursor.lastrowid

    db_conn.commit()
    return {
        "id": workflow_id,
        "message": "Workflow saved successfully",
    }


def delete_workflow_for_user(db_conn, user_id, workflow_id):
    """Delete a workflow owned by a user."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")

    cursor = db_conn.cursor()
    cursor.execute(
        "DELETE FROM workflows WHERE id = ? AND user_id = ?",
        (workflow_id, user_id),
    )
    db_conn.commit()

    return {
        "message": "Workflow deleted",
    }


def get_workflow_for_user(db_conn, user_id, workflow_id):
    """Fetch one workflow payload for a user."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT id, name, data FROM workflows WHERE id = ? AND user_id = ?",
        (workflow_id, user_id),
    )
    row = cursor.fetchone()
    if not row:
        return None

    raw_data = row[2]
    flow_data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
    return {
        "data": flow_data,
        "name": row[1],
    }
