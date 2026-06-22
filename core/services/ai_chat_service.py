"""AI chat service functions extracted from route handlers."""

import uuid
import time
import json
import os
import requests
import redis

from .service_errors import ServiceValidationError
from core.database import Database
from core.agent_middleware import AgentMiddleware
from core.config import Config
from core.logger import get_logger

logger = get_logger(__name__)

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


def create_chat_job(user_id, message, save_job_file_fn=None):
    """Create async chat job metadata and persist pending state."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")
    normalized = normalize_message(message)
    
    job_id = str(uuid.uuid4())
    
    # Use Redis if available, otherwise fallback or just return job_id
    try:
        redis_conn = redis.from_url(Config.REDIS_URL)
        redis_conn.set(f"job:{job_id}", json.dumps({"status": "pending", "user_id": user_id}))
    except Exception as e:
        logger.error("Failed to persist job status to Redis: %s", e)
        # If no Redis, we might still want to proceed if enqueuing works later,
        # but create_chat_job's job is to ensure the ID is known.
        if save_job_file_fn and callable(save_job_file_fn):
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
    return [{"role": row['role'], "content": row['content']} for row in rows]


def clear_chat_history_rows(db_conn, user_id):
    """Delete all chat history rows for a user and return affected count."""
    if user_id is None:
        raise ServiceValidationError("user_id is required")

    cursor = db_conn.cursor()
    cursor.execute("DELETE FROM ai_chat_history WHERE user_id = ?", (user_id,))
    db_conn.commit()
    return cursor.rowcount


def get_chat_job_status(job_id):
    """Validate job identifier for route-level lookup."""
    if not isinstance(job_id, str) or not job_id.strip():
        raise ServiceValidationError("job_id must be a non-empty string")
    return {
        "job_id": job_id,
    }


def background_ai_job(user_id, message, job_id):
    """Background task to call AI service and process response using Redis for persistence."""
    redis_conn = redis.from_url(Config.REDIS_URL)
    job_key = f"job:{job_id}"

    try:
        redis_conn.set(job_key, json.dumps({'status': 'processing', 'start_time': time.time(), 'user_id': user_id}))
    except Exception as e:
        logger.error("Failed to set initial status in Redis for job %s: %s", job_id, e, exc_info=True)

    try:
        db = Database()
        mw = AgentMiddleware(db)
        history_str = db.get_ai_history(user_id, limit=6)

        url = os.environ.get('HF_BASE_URL', '').rstrip('/') + '/chat'
        token = os.environ.get('HF_TOKEN')

        system_context = mw.get_system_context()
        full_msg = (
            f"[SYSTEM CONTEXT]\n{system_context}\n\n"
            f"[CONVERSATION HISTORY]\n{history_str}\n\n"
            f"[USER REQUEST]\n{message}"
        )

        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f"Bearer {token}"

        res = requests.post(
            url,
            json={'user_id': user_id, 'store_id': 1, 'message': full_msg},
            headers=headers,
            timeout=120,
        )

        if res.status_code == 200:
            ai_resp = res.json()
            ai_text = ai_resp.get('response', '')

            final_text, action = mw.process_ai_response(ai_text, user_id)

            db.add_ai_message(user_id, 'assistant', final_text)
            redis_conn.set(job_key, json.dumps({
                'status': 'completed', 
                'response': final_text, 
                'action': action,
                'user_id': user_id
            }))
        else:
            redis_conn.set(job_key, json.dumps({
                'status': 'failed', 
                'error': f"AI Error {res.status_code}",
                'user_id': user_id
            }))

    except Exception as e:
        import traceback
        full_trace = traceback.format_exc()
        logger.critical("Background AI job error for job %s: %s", job_id, e, exc_info=True)
        try:
            redis_conn.set(job_key, json.dumps({
                'status': 'failed', 
                'error': str(e), 
                'traceback': full_trace,
                'user_id': user_id
            }))
        except Exception as save_err:
            logger.critical("Failed to save error status to Redis for job %s: %s", job_id, save_err, exc_info=True)
