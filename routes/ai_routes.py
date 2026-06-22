"""AI blueprint routes and async job helpers extracted from app.py."""

import json
import os
import time

import requests
import redis
from rq import Queue
from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required

from core.database import Database
from core.services.service_errors import ServiceValidationError
from core.config import Config
from core.logger import get_logger

logger = get_logger(__name__)

ai_bp = Blueprint("ai", __name__)


@ai_bp.route('/api/ai/upload', methods=['POST'])
@login_required
def ai_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400

    file = request.files['file']
    try:
        hf_base_url = os.environ.get('HF_BASE_URL', '').rstrip('/')

        files = {'file': (file.filename, file.read(), file.mimetype)}
        data = {'user_id': current_user.id, 'store_id': 1}
        headers = {'ngrok-skip-browser-warning': 'true'}

        response = requests.post(
            f"{hf_base_url}/upload",
            files=files,
            data=data,
            headers=headers,
            timeout=60,
        )

        if response.status_code == 200:
            resp_data = response.json()
            analysis = resp_data.get('vision_analysis', 'Uploaded File')

            current_app.extensions['database'].save_attachment(
                current_user.id,
                1,
                file.filename,
                file.mimetype,
                analysis,
            )

            return jsonify(resp_data)

        return jsonify({'error': f"Upload Failed: {response.text}"}), response.status_code

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/api/ai/chat', methods=['POST'])
@login_required
def ai_chat():
    data = request.get_json(silent=True) or {}
    try:
        submitted = current_app.extensions['ai_chat_service'].submit_chat_message(current_user.id, data.get('message', ''))
    except ServiceValidationError:
        return jsonify({'error': 'Empty message'}), 400

    msg = submitted['message']
    current_app.extensions['database'].add_ai_message(current_user.id, 'user', msg)

    reply = current_app.extensions['ai_chat_service'].resolve_greeting_reply(msg)
    if reply:
        current_app.extensions['database'].add_ai_message(current_user.id, 'assistant', reply)
        return jsonify({'status': 'completed', 'response': reply, 'action': None})

    from core.services.ai_chat_service import background_ai_job
    job_data = current_app.extensions['ai_chat_service'].create_chat_job(current_user.id, msg)
    
    try:
        redis_conn = redis.from_url(Config.REDIS_URL)
        q = Queue(connection=redis_conn)
        q.enqueue(background_ai_job, current_user.id, msg, job_data['job_id'])
    except Exception as e:
        logger.error("Failed to enqueue AI job: %s", e)
        return jsonify({'error': 'Failed to start background task'}), 500

    return jsonify({'status': 'processing', 'job_id': job_data['job_id']})


@ai_bp.route('/api/ai/history', methods=['GET'])
@login_required
def get_chat_history():
    conn = None
    try:
        conn = current_app.extensions['database'].get_connection()
        history = current_app.extensions['ai_chat_service'].fetch_chat_history(conn, current_user.id, limit=50)
        return jsonify({'history': history})
    except Exception as e:
        logger.error("Error fetching chat history for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({'history': []})
    finally:
        if conn:
            conn.close()


@ai_bp.route('/api/ai/status/<job_id>', methods=['GET'])
@login_required
def ai_job_status(job_id):
    try:
        current_app.extensions['ai_chat_service'].get_chat_job_status(job_id)
    except ServiceValidationError:
        return jsonify({'status': 'failed', 'error': 'Job not found'}), 404

    try:
        redis_conn = redis.from_url(Config.REDIS_URL)
        job_data_raw = redis_conn.get(f"job:{job_id}")
        if not job_data_raw:
            return jsonify({'status': 'failed', 'error': 'Job not found'}), 404
        
        job_data = json.loads(job_data_raw)
        
        # Security: check if the job belongs to the current user
        if job_data.get('user_id') != current_user.id:
            logger.warning("User %s tried to access job %s belonging to user %s", current_user.id, job_id, job_data.get('user_id'))
            return jsonify({'status': 'failed', 'error': 'Unauthorized'}), 403
            
        return jsonify(job_data)
    except Exception as e:
        logger.error("Error fetching job status for %s: %s", job_id, e)
        return jsonify({'status': 'failed', 'error': str(e)}), 500


@ai_bp.route('/api/ai/history', methods=['DELETE'])
@login_required
def clear_chat_history():
    conn = None
    try:
        conn = current_app.extensions['database'].get_connection()
        current_app.extensions['ai_chat_service'].clear_chat_history_rows(conn, current_user.id)
        return jsonify({'status': 'success', 'message': 'Đã xóa lịch sử'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()
