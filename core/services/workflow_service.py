"""Workflow service contracts extracted from route handlers."""

from .service_errors import ServiceValidationError


def execute_user_workflow(workflow_data, google_token_raw):
    """Validate execution input and return a normalized workflow payload."""
    if not isinstance(workflow_data, dict):
        raise ServiceValidationError("workflow_data must be a dictionary")

    return {
        "workflow_data": workflow_data,
        "google_token_raw": google_token_raw,
    }


def list_workflows_for_user(db_conn, user_id):
    """Contract for fetching workflows owned by a user identifier."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")

    return []


def save_workflow_for_user(db_conn, user_id, payload):
    """Contract for persisting a workflow payload for a user."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")
    if not isinstance(payload, dict):
        raise ServiceValidationError("payload must be a dictionary")

    return {
        "user_id": user_id,
        "payload": payload,
    }
