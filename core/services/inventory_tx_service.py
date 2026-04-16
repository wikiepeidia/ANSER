"""Inventory import/export transaction service contracts."""

from .service_errors import ServiceValidationError


def create_import_transaction(db_conn, user_id, payload):
    """Validate import payload before persistence logic is delegated."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")
    if not isinstance(payload, dict):
        raise ServiceValidationError("payload must be a dictionary")

    return {
        "kind": "import",
        "user_id": user_id,
        "payload": payload,
    }


def create_export_transaction(db_conn, user_id, payload):
    """Validate export payload before persistence logic is delegated."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")
    if not isinstance(payload, dict):
        raise ServiceValidationError("payload must be a dictionary")

    return {
        "kind": "export",
        "user_id": user_id,
        "payload": payload,
    }
