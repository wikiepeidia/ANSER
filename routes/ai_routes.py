"""AI blueprint routes and async job helpers extracted from app.py."""

import json
import os
import threading
import time

import requests
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.agent_middleware import AgentMiddleware
from core.database import Database
from core.extensions import csrf
from core.services.service_errors import ServiceValidationError

ai_bp = Blueprint("ai", __name__)

JOBS_DIR = os.path.join(os.getcwd(), 'jobs')
os.makedirs(JOBS_DIR, exist_ok=True)


def _app_module():
    """Lazy app module import to avoid circular imports at module load."""
    import app as app_module

    return app_module


def save_job_file(job_id, data):
    with open(os.path.join(JOBS_DIR, f"{job_id}.json"), 'w') as f:
        json.dump(data, f)


def load_job_file(job_id):
    try:
        with open(os.path.join(JOBS_DIR, f"{job_id}.json"), 'r') as f:
            return json.load(f)
    except Exception:
        return None


def background_ai_task(job_id, user_id, message):
    import json
    import traceback

    try:
        save_job_file(job_id, {'status': 'processing', 'start_time': time.time()})
    except Exception as e:
        print(f"[ERROR] Failed to save initial job file: {e}\\n{traceback.format_exc()}")

    try:
        db = Database()
        mw = AgentMiddleware(db)
        history_str = db.get_ai_history(user_id, limit=6)

        with open('secrets/ai_config.json') as f:
            conf = json.load(f)
            url = conf.get('HF_BASE_URL').rstrip('/') + '/chat'
            token = conf.get('HF_TOKEN')

        system_context = mw.get_system_context()
        full_msg = (
            f"[SYSTEM CONTEXT]\\n{system_context}\\n\\n"
            f"[CONVERSATION HISTORY]\\n{history_str}\\n\\n"
            f"[USER REQUEST]\\n{message}"
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
            save_job_file(job_id, {'status': 'completed', 'response': final_text, 'action': action})
        else:
            save_job_file(job_id, {'status': 'failed', 'error': f"AI Error {res.status_code}"})

    except Exception as e:
        import sys
        import traceback

        full_trace = traceback.format_exc()
        exc_type, _, _ = sys.exc_info()
        print(f"[CRITICAL] Bg Thread Error: {e}")
        print(f"[CRITICAL] Error Type: {exc_type}")
        print(f"[CRITICAL] Full Traceback:\\n{full_trace}")
        try:
            save_job_file(
                job_id,
                {'status': 'failed', 'error': str(e), 'error_type': str(exc_type), 'traceback': full_trace},
            )
        except Exception as save_err:
            print(f"[CRITICAL] Failed to save job file: {save_err}")
            with open(os.path.join(JOBS_DIR, f"{job_id}.json"), 'w') as f:
                escaped = full_trace.replace(chr(34), chr(39))
                f.write(f'{{"status":"failed","error":"{str(e)}","traceback":"{escaped}"}}')


@ai_bp.route('/api/ai/upload', methods=['POST'])
@login_required
@csrf.exempt
def ai_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400

    file = request.files['file']
    try:
        with open('secrets/ai_config.json') as f:
            ai_config = json.load(f)
            hf_base_url = ai_config.get('HF_BASE_URL').rstrip('/')

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

            _app_module().db_manager.save_attachment(
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
@csrf.exempt
def ai_chat():
    data = request.get_json(silent=True) or {}
    try:
        submitted = _app_module().ai_chat_service.submit_chat_message(current_user.id, data.get('message', ''))
    except ServiceValidationError:
        return jsonify({'error': 'Empty message'}), 400

    msg = submitted['message']
    _app_module().db_manager.add_ai_message(current_user.id, 'user', msg)

    reply = _app_module().ai_chat_service.resolve_greeting_reply(msg)
    if reply:
        _app_module().db_manager.add_ai_message(current_user.id, 'assistant', reply)
        return jsonify({'status': 'completed', 'response': reply, 'action': None})

    job_data = _app_module().ai_chat_service.create_chat_job(current_user.id, msg, save_job_file)
    threading.Thread(target=background_ai_task, args=(job_data['job_id'], current_user.id, msg)).start()
    return jsonify({'status': 'processing', 'job_id': job_data['job_id']})


@ai_bp.route('/api/ai/history', methods=['GET'])
@login_required
def get_chat_history():
    conn = None
    try:
        conn = _app_module().db_manager.get_connection()
        history = _app_module().ai_chat_service.fetch_chat_history(conn, current_user.id, limit=50)
        return jsonify({'history': history})
    except Exception as e:
        print(f"History Error: {e}")
        return jsonify({'history': []})
    finally:
        if conn:
            conn.close()


@ai_bp.route('/api/ai/status/<job_id>', methods=['GET'])
@login_required
def ai_job_status(job_id):
    try:
        _app_module().ai_chat_service.get_chat_job_status(job_id)
    except ServiceValidationError:
        return jsonify({'status': 'failed', 'error': 'Job not found'}), 404

    job = load_job_file(job_id)
    if not job:
        return jsonify({'status': 'failed', 'error': 'Job not found'}), 404
    return jsonify(job)


@ai_bp.route('/api/ai/history', methods=['DELETE'])
@login_required
def clear_chat_history():
    conn = None
    try:
        conn = _app_module().db_manager.get_connection()
        _app_module().ai_chat_service.clear_chat_history_rows(conn, current_user.id)
        return jsonify({'status': 'success', 'message': 'History cleared'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()
