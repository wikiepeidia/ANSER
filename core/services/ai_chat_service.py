"""AI chat service contracts extracted from route handlers."""

from .service_errors import ServiceValidationError


def submit_chat_message(user_id, message):
    """Validate and normalize a chat submission payload."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")
    if not isinstance(message, str) or not message.strip():
        raise ServiceValidationError("message must be a non-empty string")

    return {
        "user_id": user_id,
        "message": message.strip(),
    }


def get_chat_history_rows(db_conn, user_id, limit=50):
    """Contract for fetching recent chat history rows."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")
    if not isinstance(limit, int) or limit <= 0:
        raise ServiceValidationError("limit must be a positive integer")

    return []


def get_chat_job_status(job_id):
    """Contract for retrieving asynchronous chat job status."""
    if not isinstance(job_id, str) or not job_id.strip():
        raise ServiceValidationError("job_id must be a non-empty string")

    return {
        "job_id": job_id,
        "status": "unknown",
    }
