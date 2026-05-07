"""Workflow blueprint routes extracted from app.py."""

import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required

from core.extensions import csrf

workflow_bp = Blueprint("workflow", __name__)


def _app_module():
    """Lazy app module import to avoid circular imports at module load."""
    import app as app_module

    return app_module


@workflow_bp.route('/api/workflows', methods=['GET'])
@login_required
def get_user_workflows():
    conn = None
    try:
        app_module = _app_module()
        conn = app_module.db.get_connection()
        workflows = app_module.workflow_service.list_workflows_for_user(conn, app_module.current_user.id)
        return jsonify({'success': True, 'workflows': workflows})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()


@workflow_bp.route('/api/workflows', methods=['POST'])
@login_required
def save_workflow():
    conn = None
    try:
        app_module = _app_module()
        payload = request.get_json(silent=True) or {}
        conn = app_module.db.get_connection()
        result = app_module.workflow_service.save_workflow_for_user(conn, app_module.current_user.id, payload)
        return jsonify({'success': True, 'id': result['id'], 'message': result['message']})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()


@workflow_bp.route('/api/workflows/<int:workflow_id>', methods=['DELETE'])
@login_required
def delete_workflow(workflow_id):
    conn = None
    try:
        app_module = _app_module()
        conn = app_module.db.get_connection()
        result = app_module.workflow_service.delete_workflow_for_user(conn, app_module.current_user.id, workflow_id)
        return jsonify({'success': True, 'message': result['message']})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()


@workflow_bp.route('/api/workflows/<int:workflow_id>', methods=['GET'])
@login_required
def get_single_workflow(workflow_id):
    conn = None
    try:
        app_module = _app_module()
        conn = app_module.db_manager.get_connection()
        result = app_module.workflow_service.get_workflow_for_user(conn, app_module.current_user.id, workflow_id)
        if result:
            return jsonify({'success': True, 'data': result['data'], 'name': result['name']})
        return jsonify({'success': False}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@workflow_bp.route('/api/workflow/execute', methods=['POST'])
@login_required
@csrf.exempt
def run_workflow():
    try:
        app_module = _app_module()
        workflow_data = request.get_json(silent=True) or {}
        result = app_module.workflow_service.execute_user_workflow(workflow_data, app_module.current_user.google_token)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@workflow_bp.route('/api/workflow/upload_file', methods=['POST'])
@login_required
def api_workflow_upload_file():
    """Upload a file for workflow configuration."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    try:
        upload_dir = os.path.join(current_app.root_path, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        from werkzeug.utils import secure_filename

        filename = secure_filename(file.filename)
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"{timestamp}_{filename}"

        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        return jsonify(
            {
                'success': True,
                'path': file_path,
                'filename': filename,
                'message': 'File uploaded successfully',
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
