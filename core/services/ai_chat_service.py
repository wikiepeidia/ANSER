"""AI chat service functions extracted from route handlers."""

import uuid

from .service_errors import ServiceValidationError


_GREETINGS = ("xin chào", "hello", "hi", "chào")


def normalize_message(raw_message):
    """Normalize and validate a chat message."""
    if not isinstance(raw_message, str):
        raise ServiceValidationError("message must be a string")
    message = raw_message.strip()
    if not message:
        raise ServiceValidationError("message must be non-empty")
    return message


def resolve_greeting_reply(message):
    """Return canned greeting response when a short greeting is detected."""
    normalized = normalize_message(message).lower()
    if any(normalized.startswith(greeting) for greeting in _GREETINGS) and len(normalized) < 20:
        return (
            "Xin chào! Tôi là trợ lý ảo Project A. "
            "Tôi có thể giúp bạn tạo quy trình tự động hóa hoặc tra cứu dữ liệu."
        )
    return None


def submit_chat_message(user_id, message):
    """Validate and normalize a chat submission payload."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")
    return {
        "user_id": user_id,
        "message": normalize_message(message),
    }


def create_chat_job(user_id, message, save_job_file_fn):
    """Create async chat job metadata and persist pending state."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")
    normalized = normalize_message(message)
    if not callable(save_job_file_fn):
        raise ServiceValidationError("save_job_file_fn must be callable")

    job_id = str(uuid.uuid4())
    save_job_file_fn(job_id, {"status": "pending"})
    return {
        "status": "processing",
        "job_id": job_id,
        "message": normalized,
    }


def get_chat_history_rows(db_conn, user_id, limit=50):
    """Return raw chat history rows for a user."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")
    if not isinstance(limit, int) or limit <= 0:
        raise ServiceValidationError("limit must be a positive integer")

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT role, content FROM ai_chat_history WHERE user_id = ? "
        "ORDER BY created_at ASC LIMIT ?",
        (user_id, limit),
    )
    return cursor.fetchall()


def fetch_chat_history(db_conn, user_id, limit=50):
    """Return formatted chat history suitable for HTTP JSON responses."""
    rows = get_chat_history_rows(db_conn, user_id, limit=limit)
    return [{"role": row[0], "content": row[1]} for row in rows]


def clear_chat_history_rows(db_conn, user_id):
    """Delete all chat history rows for a user and return affected count."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM ai_chat_history WHERE user_id = ?", (user_id,))
    db_conn.commit()
    return cursor.rowcount


def get_chat_job_status(job_id):
    """Validate job identifier for route-level file lookup."""
    if not isinstance(job_id, str) or not job_id.strip():
        raise ServiceValidationError("job_id must be a non-empty string")
    return {
        "job_id": job_id,
    }
