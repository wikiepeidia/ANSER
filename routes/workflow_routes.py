"""Workflow blueprint routes extracted from app.py."""

import json
import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from core.logger import get_logger
from core.security import safe_api_error, validate_upload

workflow_bp = Blueprint("workflow", __name__)
logger = get_logger(__name__)

WORKFLOW_UPLOAD_EXTENSIONS = {'pdf', 'txt', 'csv', 'json', 'xlsx', 'xls', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'webp'}
WORKFLOW_UPLOAD_MIMETYPES = {
    'application/pdf',
    'text/plain',
    'text/csv',
    'application/json',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/png',
    'image/jpeg',
    'image/webp',
}


@workflow_bp.route('/api/workflows', methods=['GET'])
@login_required
def get_user_workflows():
    conn = None
    try:
        conn = current_app.extensions['database'].get_business_connection()
        workflows = current_app.extensions['workflow_service'].list_workflows_for_user(conn, current_user.id)
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
        payload = request.get_json(silent=True) or {}
        conn = current_app.extensions['database'].get_business_connection()
        result = current_app.extensions['workflow_service'].save_workflow_for_user(conn, current_user.id, payload)
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
        conn = current_app.extensions['database'].get_business_connection()
        result = current_app.extensions['workflow_service'].delete_workflow_for_user(conn, current_user.id, workflow_id)
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
        conn = current_app.extensions['database'].get_business_connection()
        result = current_app.extensions['workflow_service'].get_workflow_for_user(conn, current_user.id, workflow_id)
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
def run_workflow():
    try:
        workflow_data = request.get_json(silent=True) or {}
        result = current_app.extensions['workflow_service'].execute_user_workflow(workflow_data, current_user.google_token)
        return jsonify(result)
    except Exception as e:
        return safe_api_error(logger, exc=e)


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
        validate_upload(file, WORKFLOW_UPLOAD_EXTENSIONS, WORKFLOW_UPLOAD_MIMETYPES)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

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
                'message': 'Tải file lên thành công',
            }
        )
    except Exception as e:
        return safe_api_error(logger, exc=e)


@workflow_bp.route('/api/iot-events', methods=['GET'])
@login_required
def iot_events_list():
    """Return recent IoT events with optional filters."""
    device_id  = request.args.get('device_id', '').strip()
    event_type = request.args.get('event_type', '').strip()
    limit      = min(int(request.args.get('limit', 50)), 200)
    offset     = int(request.args.get('offset', 0))
    db = current_app.extensions['database']
    try:
        conn = db.get_business_connection()
        cur  = conn.cursor()
        ph = '%s' if db.use_postgres else '?'
        where, params = [], []
        if device_id:
            where.append(f"device_id = {ph}"); params.append(device_id)
        if event_type:
            where.append(f"event_type = {ph}"); params.append(event_type)
        w = ("WHERE " + " AND ".join(where)) if where else ""
        params_count = list(params)
        params += [limit, offset]
        cur.execute(
            f"SELECT id, device_id, event_type, payload, created_at FROM iot_events {w} "
            f"ORDER BY id DESC LIMIT {ph} OFFSET {ph}", params,
        )
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            if hasattr(r['created_at'], 'isoformat'):
                r['created_at'] = r['created_at'].isoformat()
            if isinstance(r['payload'], str):
                try:
                    r['payload'] = json.loads(r['payload'])
                except Exception:
                    pass
        cur.execute(f"SELECT COUNT(*) as total FROM iot_events {w}", params_count)
        total = cur.fetchone()['total']
        conn.close()
        return jsonify({'success': True, 'events': rows, 'total': total})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@workflow_bp.route('/api/iot-events/stats', methods=['GET'])
@login_required
def iot_events_stats():
    """Return aggregated stats: total, revenue, by-device, by-type, today.

    Postgres path uses SQL aggregates (payload is jsonb there). SQLite
    stores payload as plain TEXT and has neither the ->> operator nor
    FILTER (WHERE ...), so the SQLite path fetches raw rows and computes
    the same aggregates in Python instead of forking the SQL two ways.
    """
    db = current_app.extensions['database']
    try:
        conn = db.get_business_connection()
        cur = conn.cursor()

        if db.use_postgres:
            cur.execute("""
                SELECT
                    COUNT(*) as total_events,
                    COUNT(DISTINCT device_id) as device_count,
                    COALESCE(SUM((payload->>'amount')::numeric), 0) as total_revenue,
                    COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE) as today_events
                FROM iot_events
            """)
            summary = dict(cur.fetchone())
            summary['total_revenue'] = float(summary['total_revenue'])

            cur.execute("""
                SELECT device_id, COUNT(*) as count,
                       COALESCE(SUM((payload->>'amount')::numeric), 0) as revenue
                FROM iot_events GROUP BY device_id ORDER BY count DESC LIMIT 10
            """)
            by_device = [dict(r) for r in cur.fetchall()]
            for r in by_device:
                r['revenue'] = float(r['revenue'])

            cur.execute("SELECT event_type, COUNT(*) as count FROM iot_events GROUP BY event_type ORDER BY count DESC")
            by_type = [dict(r) for r in cur.fetchall()]
        else:
            cur.execute("SELECT device_id, event_type, payload, created_at FROM iot_events")
            rows = cur.fetchall()
            today = datetime.now().strftime('%Y-%m-%d')
            devices, types = {}, {}
            total_revenue, today_events = 0.0, 0
            for r in rows:
                payload = r['payload']
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        payload = {}
                amount = float((payload or {}).get('amount') or 0)
                total_revenue += amount
                if str(r['created_at'])[:10] == today:
                    today_events += 1
                dev = devices.setdefault(r['device_id'], {'device_id': r['device_id'], 'count': 0, 'revenue': 0.0})
                dev['count'] += 1
                dev['revenue'] += amount
                types[r['event_type']] = types.get(r['event_type'], 0) + 1

            summary = {
                'total_events': len(rows), 'device_count': len(devices),
                'total_revenue': total_revenue, 'today_events': today_events,
            }
            by_device = sorted(devices.values(), key=lambda d: d['count'], reverse=True)[:10]
            by_type = [{'event_type': k, 'count': v} for k, v in
                       sorted(types.items(), key=lambda kv: kv[1], reverse=True)]

        conn.close()
        return jsonify({'success': True, 'summary': summary, 'by_device': by_device, 'by_type': by_type})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
