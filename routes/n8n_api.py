"""n8n API integration — ANSER gọi n8n REST API, không dùng proxy/iframe."""

import os
import secrets
import json
import glob
import hmac

import requests as _req
from flask import Blueprint, jsonify, request
from flask_login import login_required

from core.config import Config
from core.logger import get_logger
import core.services.invoice_draft_service as invoice_draft_service
from core.services.service_errors import ServiceValidationError

logger = get_logger(__name__)

n8n_api_bp = Blueprint('n8n_api', __name__)

_N8N_ORIGIN = Config.N8N_ORIGIN
_CREDS_FILE = os.path.join(os.path.dirname(__file__), '..', '.n8n_creds.json')
_TEMPLATES  = os.path.join(os.path.dirname(__file__), '..', 'workflow_templates')
_auth_token = None
_login_fail_until = 0


# ── Credentials ───────────────────────────────────────────────────────────────

def _load_creds():
    try:
        if os.path.exists(_CREDS_FILE):
            with open(_CREDS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _save_creds(email, password):
    try:
        with open(_CREDS_FILE, 'w') as f:
            json.dump({'email': email, 'password': password}, f)
    except Exception as e:
        logger.error('[n8n] Cannot save credentials: %s', e)


def _get_creds():
    email = os.environ.get('N8N_ADMIN_EMAIL', '')
    pwd   = os.environ.get('N8N_ADMIN_PASSWORD', '')
    if email and pwd:
        return email, pwd
    saved = _load_creds()
    if saved:
        return saved.get('email', ''), saved.get('password', '')
    return '', ''


# ── Auto Setup ────────────────────────────────────────────────────────────────

def _needs_setup():
    try:
        r = _req.get(f'{_N8N_ORIGIN}/rest/settings', timeout=5)
        if r.status_code == 200:
            um = r.json().get('data', {}).get('userManagement', {})
            if 'showSetupOnFirstLoad' in um:
                return um['showSetupOnFirstLoad']
            return not um.get('isInstanceOwnerSetUp', True)
    except Exception:
        pass
    return False


def _auto_setup():
    # _needs_setup() already confirmed this n8n instance has no owner yet —
    # always run setup here. Reuse a cached email/password if one exists
    # (e.g. from a prior volume) so the credential stays stable across
    # restarts, but never skip the actual /rest/owner/setup call: skipping
    # it left stale creds pointing at an instance that was never set up,
    # breaking every subsequent n8n API call with a silent 401 loop.
    saved = _load_creds()
    email    = saved['email'] if saved else 'admin@anser.local'
    password = saved['password'] if saved else secrets.token_urlsafe(16)
    try:
        r = _req.post(f'{_N8N_ORIGIN}/rest/owner/setup', json={
            'email': email, 'password': password,
            'firstName': 'ANSER', 'lastName': 'Admin',
        }, timeout=10)
        if r.status_code in (200, 201):
            _save_creds(email, password)
            logger.info('[n8n] Auto-setup complete: %s', email)
            return email, password
        logger.error('[n8n] Setup failed %s: %s', r.status_code, r.text[:200])
    except Exception as e:
        logger.error('[n8n] Setup error: %s', e)
    return '', ''


# ── Auth ─────────────────────────────────────────────────────────────────────

def _login():
    global _auth_token, _login_fail_until
    import time
    now = time.time()
    if now < _login_fail_until:
        return False
    try:
        if _needs_setup():
            _auto_setup()
    except Exception:
        pass
    email, pwd = _get_creds()
    if not email or not pwd:
        _login_fail_until = now + 60
        return False
    try:
        r = _req.post(f'{_N8N_ORIGIN}/rest/login',
                      json={'emailOrLdapLoginId': email, 'password': pwd}, timeout=5)
        if r.status_code == 200:
            _auth_token = r.cookies.get('n8n-auth')
            _login_fail_until = 0
            logger.info('[n8n] Authenticated as %s', email)
            return True
        _login_fail_until = now + 30
        logger.warning('[n8n] Login failed (%s)', r.status_code)
    except Exception as exc:
        logger.error('[n8n] Cannot reach n8n: %s', exc)
        _login_fail_until = now + 15
    return False


def _ensure_auth():
    if not _auth_token:
        _login()


def _headers():
    h = {'Content-Type': 'application/json'}
    if _auth_token:
        h['Cookie'] = f'n8n-auth={_auth_token}'
    return h


def _n8n_request(method, path, **kwargs):
    _ensure_auth()
    url = f'{_N8N_ORIGIN}/rest/{path}'
    try:
        r = _req.request(method, url, headers=_headers(),
                         timeout=kwargs.get('timeout', 10), **{
                             k: v for k, v in kwargs.items() if k != 'timeout'})
        if r.status_code == 401:
            global _auth_token
            _auth_token = None
            if _login():
                r = _req.request(method, url, headers=_headers(),
                                 timeout=10, **{
                                     k: v for k, v in kwargs.items() if k != 'timeout'})
        return r
    except Exception as exc:
        logger.error('[n8n] Request failed %s %s: %s', method, path, exc)
        return None


def _n8n_get(path, **kwargs):
    return _n8n_request('GET', path, **kwargs)


def _n8n_post(path, data=None, **kwargs):
    return _n8n_request('POST', path, json=data, **kwargs)


def _n8n_patch(path, data=None):
    return _n8n_request('PATCH', path, json=data)


def _n8n_delete(path):
    return _n8n_request('DELETE', path)


# ── API Routes ────────────────────────────────────────────────────────────────

@n8n_api_bp.route('/api/n8n/status', methods=['GET'])
@login_required
def n8n_status():
    try:
        r = _req.get(f'{_N8N_ORIGIN}/healthz', timeout=3)
        return jsonify({'success': True, 'online': r.status_code < 500,
                        'authenticated': _auth_token is not None})
    except Exception:
        return jsonify({'success': True, 'online': False, 'authenticated': False})


@n8n_api_bp.route('/api/n8n/workflows', methods=['GET'])
@login_required
def list_workflows():
    r = _n8n_get('workflows?includeScopes=true')
    if not r or r.status_code != 200:
        return jsonify({'success': False, 'error': 'Cannot reach n8n'}), 502
    workflows = r.json().get('data', [])
    result = []
    for wf in workflows:
        result.append({
            'id':        wf.get('id'),
            'name':      wf.get('name'),
            'active':    wf.get('active', False),
            'nodes':     len(wf.get('nodes', [])),
            'updatedAt': wf.get('updatedAt'),
            'createdAt': wf.get('createdAt'),
            'tags':      [t.get('name') for t in wf.get('tags', [])],
        })
    return jsonify({'success': True, 'workflows': result})


@n8n_api_bp.route('/api/n8n/workflows/<wf_id>/run', methods=['POST'])
@login_required
def run_workflow(wf_id):
    try:
        return _do_run_workflow(wf_id)
    except Exception as exc:
        logger.error('[n8n] Run failed: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500


def _do_run_workflow(wf_id):
    test_data = (request.get_json(silent=True) or {}).get('testData', {})

    wf_r = _n8n_get(f'workflows/{wf_id}')
    if not wf_r or wf_r.status_code != 200:
        return jsonify({'success': False, 'error': 'Cannot load workflow'}), 502

    wf = wf_r.json().get('data', wf_r.json())
    nodes = wf.get('nodes', [])
    active = wf.get('active', False)

    trigger_type, trigger_node = _detect_trigger(nodes)

    # Auto-activate if needed
    if not active and trigger_type in ('webhook', 'schedule'):
        vid = wf.get('versionId')
        act_r = _n8n_post(f'workflows/{wf_id}/activate', data={'versionId': vid})
        if act_r and act_r.status_code == 200:
            active = act_r.json().get('data', {}).get('active', False)
        if not active:
            return jsonify({'success': False,
                            'error': 'Không thể kích hoạt workflow. '
                                     'Liên hệ quản trị viên để kiểm tra cấu hình.'}), 400

    if trigger_type == 'webhook':
        webhook_path = trigger_node.get('parameters', {}).get('path', '')
        if not webhook_path:
            return jsonify({'success': False,
                            'error': 'Webhook path chưa cấu hình cho template này.'}), 400
        if not active:
            return jsonify({'success': False,
                            'error': 'Workflow chưa active. Liên hệ quản trị viên cấu hình credentials.'}), 400
        url = f'{_N8N_ORIGIN}/webhook/{webhook_path}'
        method = trigger_node.get('parameters', {}).get('httpMethod', 'POST').upper()
        try:
            if method == 'GET':
                r = _req.get(url, params=test_data, timeout=30)
            else:
                payload = test_data or {'test': True, 'source': 'ANSER'}
                discord_url = os.environ.get('DISCORD_WEBHOOK_URL', '')
                if discord_url:
                    payload['discord_url'] = discord_url
                r = _req.post(url, json=payload, timeout=30)
            try:
                body = r.json()
            except Exception:
                body = r.text[:500]
            return jsonify({'success': r.status_code < 400,
                            'message': f'HTTP {r.status_code}',
                            'response': body,
                            'webhookResponse': r.status_code})
        except Exception as exc:
            return jsonify({'success': False, 'error': str(exc)}), 502

    elif trigger_type == 'schedule':
        if not active:
            return jsonify({'success': False,
                            'error': 'Không thể kích hoạt. Liên hệ quản trị viên cấu hình credentials.'}), 400
        return jsonify({'success': True,
                        'message': 'Workflow đã kích hoạt! Chạy tự động theo lịch.'})

    elif trigger_type == 'manual':
        return jsonify({'success': False,
                        'error': 'Workflow này không hỗ trợ chạy trực tiếp từ giao diện.'}), 400
    else:
        return jsonify({'success': False,
                        'error': 'Không xác định được cách chạy workflow này.'}), 400


@n8n_api_bp.route('/api/n8n/workflows/<wf_id>', methods=['DELETE'])
@login_required
def delete_workflow(wf_id):
    _n8n_patch(f'workflows/{wf_id}', data={'active': False})
    _n8n_post(f'workflows/{wf_id}/archive')
    r = _n8n_delete(f'workflows/{wf_id}')
    if not r:
        return jsonify({'success': False, 'error': 'Cannot reach n8n'}), 502
    if r.status_code in (200, 204):
        return jsonify({'success': True, 'message': 'Đã xóa workflow'})
    return jsonify({'success': False, 'error': f'n8n: {r.status_code}'}), 502


@n8n_api_bp.route('/api/n8n/internal/iot-events', methods=['GET'])
def internal_iot_events():
    """Internal endpoint for n8n workflows — no auth required."""
    from flask import current_app
    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available', 'events': []})
    limit = request.args.get('limit', 10, type=int)
    try:
        conn = db.get_business_connection()
        cursor = conn.cursor()
        if db.use_postgres:
            cursor.execute('SELECT id, device_id, event_type, payload, created_at '
                           'FROM iot_events ORDER BY created_at DESC LIMIT %s', (limit,))
        else:
            cursor.execute('SELECT id, device_id, event_type, payload, created_at '
                           'FROM iot_events ORDER BY created_at DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        events = []
        for r in rows:
            row = dict(r) if hasattr(r, 'keys') else dict(zip(
                [d[0] for d in cursor.description], r))
            if isinstance(row.get('payload'), str):
                try:
                    row['payload'] = json.loads(row['payload'])
                except Exception:
                    pass
            if hasattr(row.get('created_at'), 'isoformat'):
                row['created_at'] = row['created_at'].isoformat()
            events.append(row)
        conn.close()
        return jsonify({'success': True, 'events': events, 'total': len(events)})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc), 'events': []})


@n8n_api_bp.route('/api/n8n/internal/warehouses', methods=['GET'])
def internal_warehouses():
    """Internal endpoint for n8n workflows — no auth required.

    Returns active warehouse alert profiles (threshold + Discord webhook)
    for the low_stock_alert workflow to loop over.
    """
    from flask import current_app
    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available', 'warehouses': []})
    try:
        conn = db.get_business_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, low_stock_threshold, discord_webhook_url '
            'FROM warehouses WHERE is_active = 1 ORDER BY name'
        )
        rows = cursor.fetchall()
        warehouses = [
            dict(r) if hasattr(r, 'keys') else dict(zip([d[0] for d in cursor.description], r))
            for r in rows
        ]
        conn.close()
        return jsonify({'success': True, 'warehouses': warehouses})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc), 'warehouses': []})


@n8n_api_bp.route('/api/n8n/internal/low-stock', methods=['GET'])
def internal_low_stock():
    """Internal endpoint for n8n workflows — no auth required.

    Replaces the old rag-service call (that service no longer exists).
    """
    from flask import current_app
    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available', 'items': []})
    threshold = request.args.get('threshold', 10, type=int)
    try:
        conn = db.get_business_connection()
        cursor = conn.cursor()
        if db.use_postgres:
            cursor.execute(
                'SELECT name, code, stock_quantity, price FROM products '
                'WHERE stock_quantity < %s ORDER BY stock_quantity ASC', (threshold,)
            )
        else:
            cursor.execute(
                'SELECT name, code, stock_quantity, price FROM products '
                'WHERE stock_quantity < ? ORDER BY stock_quantity ASC', (threshold,)
            )
        rows = cursor.fetchall()
        items = [
            dict(r) if hasattr(r, 'keys') else dict(zip([d[0] for d in cursor.description], r))
            for r in rows
        ]
        conn.close()
        return jsonify({'success': True, 'threshold': threshold, 'count': len(items), 'items': items})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc), 'items': []})


@n8n_api_bp.route('/api/n8n/internal/invoice-import-draft', methods=['POST'])
def internal_invoice_import_draft():
    """Internal endpoint for n8n workflows — shared-secret auth required.

    Receives a clean, VLM-extracted invoice (Brain's real /ocr response
    shape) and writes it as a pending_review import draft. Never mutates
    live stock, never trusts a client-supplied status. See 02-CONTEXT.md
    for the full request/response contract.
    """
    from flask import current_app

    # Read fresh per-request (not cached at module import time like
    # _N8N_ORIGIN above) so the token can be reconfigured/monkeypatched
    # independently of module import order.
    expected = Config.ANSER_N8N_INTERNAL_TOKEN
    provided = request.headers.get('X-Webhook-Token', '')
    if not expected or not hmac.compare_digest(provided, expected):
        return jsonify({'success': False, 'error': 'unauthorized'}), 401

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({'success': False, 'error': 'invalid_json_body'}), 400

    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available'}), 500

    conn = db.get_business_connection()
    try:
        result = invoice_draft_service.create_invoice_draft(conn, body)
    except ServiceValidationError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    except Exception as exc:
        logger.error('[n8n] invoice-import-draft failed: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        conn.close()

    return jsonify({'success': True, **result}), 200


def _detect_trigger(nodes):
    """Return (trigger_type, trigger_node) for a workflow's nodes."""
    for n in nodes:
        ntype = n.get('type', '').lower()
        if 'webhook' in ntype:
            return 'webhook', n
        if 'schedule' in ntype or 'cron' in ntype:
            return 'schedule', n
        if 'manualtrigger' in ntype:
            return 'manual', n
    return 'unknown', {}


@n8n_api_bp.route('/api/n8n/workflows/<wf_id>/activate', methods=['POST'])
@login_required
def toggle_workflow(wf_id):
    want_active = (request.get_json(silent=True) or {}).get('active', True)

    if want_active:
        wf_r = _n8n_get(f'workflows/{wf_id}')
        if not wf_r or wf_r.status_code != 200:
            return jsonify({'success': False, 'error': 'Cannot reach n8n'}), 502
        vid = wf_r.json().get('data', {}).get('versionId')
        r = _n8n_post(f'workflows/{wf_id}/activate', data={'versionId': vid})
    else:
        r = _n8n_post(f'workflows/{wf_id}/deactivate')

    if not r:
        return jsonify({'success': False, 'error': 'Cannot reach n8n'}), 502
    if r.status_code == 200:
        actual = r.json().get('data', {}).get('active', False)
        return jsonify({'success': True, 'active': actual})
    return jsonify({'success': False,
                    'error': f'n8n: {r.status_code} - {r.text[:200]}'}), 502


@n8n_api_bp.route('/api/n8n/workflows/<wf_id>/executions', methods=['GET'])
@login_required
def list_executions(wf_id):
    r = _n8n_get(f'executions?workflowId={wf_id}&limit=10')
    if not r or r.status_code != 200:
        return jsonify({'success': False, 'error': 'Cannot reach n8n'}), 502
    execs = r.json().get('data', [])
    result = []
    for ex in execs:
        result.append({
            'id':         ex.get('id'),
            'status':     ex.get('status'),
            'startedAt':  ex.get('startedAt'),
            'stoppedAt':  ex.get('stoppedAt'),
            'mode':       ex.get('mode'),
        })
    return jsonify({'success': True, 'executions': result})


# ── Template API ─────────────────────────────────────────────────────────────

_TEMPLATE_META = {
    'iot_pos_demo':         {'icon': 'fa-cash-register',  'color': '#FF6B35', 'label': 'POS → NeonDB → Discord',     'desc': 'Nhận sự kiện POS, lưu DB, thông báo Discord'},
    'daily_sales_report':   {'icon': 'fa-chart-bar',      'color': '#306699', 'label': 'Báo cáo doanh số hàng ngày', 'desc': 'Mỗi 20h tổng hợp sales → Discord embed'},
    'low_stock_alert':      {'icon': 'fa-boxes',          'color': '#FF9800', 'label': 'Cảnh báo tồn kho thấp',      'desc': 'Mỗi 6h check stock < 10 → Discord cảnh báo'},
    'new_customer_welcome': {'icon': 'fa-user-plus',      'color': '#34A700', 'label': 'Khách hàng mới → Welcome',   'desc': 'Webhook nhận KH mới → NeonDB → Discord'},
    'ai_security_analyzer': {'icon': 'fa-shield-alt',     'color': '#E91E63', 'label': 'AI Security Log Analyzer',   'desc': 'Phân tích log bảo mật bằng LLM + RAG'},
    'iot_events_ingest':    {'icon': 'fa-satellite-dish',  'color': '#009688', 'label': 'IoT Events Ingest',          'desc': 'Webhook nhận IoT event → NeonDB'},
    'sample_schedule_http': {'icon': 'fa-clock',           'color': '#607D8B', 'label': 'Schedule + HTTP Request',   'desc': 'Chạy định kỳ, gọi API bên ngoài'},
    'sample_webhook_echo':  {'icon': 'fa-bolt',            'color': '#795548', 'label': 'Webhook Echo',              'desc': 'Nhận webhook và trả response'},
    'query_neondb':         {'icon': 'fa-database',        'color': '#00BCD4', 'label': 'Query NeonDB',              'desc': 'Truy vấn IoT events từ NeonDB → trả kết quả ngay'},
    'notify_discord':       {'icon': 'fa-comment-dots',    'color': '#5865F2', 'label': 'Notify Discord',            'desc': 'Lấy data NeonDB → gửi embed đẹp lên Discord'},
    'order_discord_notify': {'icon': 'fa-shopping-cart',   'color': '#4CAF50', 'label': 'Đơn hàng → Discord',       'desc': 'Nhập/xuất kho → tự động thông báo Discord'},
}


@n8n_api_bp.route('/api/n8n/templates', methods=['GET'])
@login_required
def list_templates():
    templates = []
    for fp in sorted(glob.glob(os.path.join(_TEMPLATES, '*.json'))):
        slug = os.path.splitext(os.path.basename(fp))[0]
        meta = _TEMPLATE_META.get(slug, {})
        try:
            with open(fp, encoding='utf-8') as f:
                wf = json.load(f)
            templates.append({
                'slug':       slug,
                'name':       wf.get('name', slug),
                'node_count': len(wf.get('nodes', [])),
                'icon':       meta.get('icon', 'fa-project-diagram'),
                'color':      meta.get('color', '#667eea'),
                'label':      meta.get('label', wf.get('name', slug)),
                'desc':       meta.get('desc', ''),
            })
        except Exception:
            pass
    return jsonify({'success': True, 'templates': templates})


@n8n_api_bp.route('/api/n8n/templates/deploy', methods=['POST'])
@login_required
def deploy_template():
    slug = (request.get_json(silent=True) or {}).get('slug', '')
    fp   = os.path.join(_TEMPLATES, f'{slug}.json')
    if not slug or not os.path.isfile(fp):
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    try:
        with open(fp, encoding='utf-8') as f:
            wf = json.load(f)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    _ensure_auth()
    wf_name = wf.get('name', slug)

    # Check existing — unarchive if needed
    r = _n8n_get('workflows')
    if r and r.status_code == 200:
        for w in r.json().get('data', []):
            if w.get('name') == wf_name:
                if w.get('isArchived'):
                    _n8n_post(f'workflows/{w["id"]}/unarchive')
                return jsonify({'success': True, 'message': 'Đã tồn tại',
                                'id': w['id'], 'existing': True})

    r = _n8n_post('workflows', data=wf)
    if r and r.status_code in (200, 201):
        data = r.json().get('data', {})
        return jsonify({'success': True, 'message': 'Import thành công!',
                        'id': data.get('id'), 'name': wf_name})
    return jsonify({'success': False, 'error': 'Import failed'}), 502
