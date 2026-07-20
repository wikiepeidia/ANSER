"""n8n API integration for San Xuat — separate n8n instance/port from ANSER's.

Mirrors ANSER's routes/n8n_api.py pattern (auto-setup, cookie auth, template
deploy) but talks to San Xuat's own n8n container (Config.N8N_ORIGIN) and
its own workflow_templates/ (manuf_*.json, sourced from demo_wokflow).

The manuf templates call back into this app via {{ $env.RAG_BASE_URL }},
{{ $env.BRAIN_BASE_URL }}, {{ $env.NOTIFY_URL }} (set in docker-compose.yml).
RAG_BASE_URL/NOTIFY_URL land on real internal endpoints below that write to
San Xuat's own `automation_events` table. BRAIN_BASE_URL (OCR/LLM) has no
real backing service in this project — its endpoints return a clearly
labelled mock response so a full workflow run still completes end-to-end.
"""

import os
import logging
import secrets
import json
import glob

import requests as _req
from flask import Blueprint, jsonify, request
from flask_login import login_required

from core.config import Config
from core.extensions import csrf
from core.sanxuat_db import get_connection, now
from routes.inventory_routes import _find_material, _resolve_supplier

logger = logging.getLogger(__name__)

n8n_api_bp = Blueprint('n8n_api', __name__)

_N8N_ORIGIN = Config.N8N_ORIGIN
_CREDS_FILE = os.path.join(os.path.dirname(__file__), '..', '.n8n_sx_creds.json')
_TEMPLATES = os.path.join(os.path.dirname(__file__), '..', 'workflow_templates')
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
        logger.error('[n8n-sx] Cannot save credentials: %s', e)


def _get_creds():
    email = os.environ.get('N8N_SX_ADMIN_EMAIL', '')
    pwd = os.environ.get('N8N_SX_ADMIN_PASSWORD', '')
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
    saved = _load_creds()
    email = saved['email'] if saved else 'admin@anser-sanxuat.local'
    password = saved['password'] if saved else secrets.token_urlsafe(16)
    try:
        r = _req.post(f'{_N8N_ORIGIN}/rest/owner/setup', json={
            'email': email, 'password': password,
            'firstName': 'ANSER', 'lastName': 'SanXuat',
        }, timeout=10)
        if r.status_code in (200, 201):
            _save_creds(email, password)
            logger.info('[n8n-sx] Auto-setup complete: %s', email)
            return email, password
        logger.error('[n8n-sx] Setup failed %s: %s', r.status_code, r.text[:200])
    except Exception as e:
        logger.error('[n8n-sx] Setup error: %s', e)
    return '', ''


# ── Auth ─────────────────────────────────────────────────────────────────────

def _login():
    global _auth_token, _login_fail_until
    import time
    now_ts = time.time()
    if now_ts < _login_fail_until:
        return False
    try:
        if _needs_setup():
            _auto_setup()
    except Exception:
        pass
    email, pwd = _get_creds()
    if not email or not pwd:
        _login_fail_until = now_ts + 60
        return False
    try:
        r = _req.post(f'{_N8N_ORIGIN}/rest/login',
                      json={'emailOrLdapLoginId': email, 'password': pwd}, timeout=5)
        if r.status_code == 200:
            _auth_token = r.cookies.get('n8n-auth')
            _login_fail_until = 0
            logger.info('[n8n-sx] Authenticated as %s', email)
            return True
        _login_fail_until = now_ts + 30
        logger.warning('[n8n-sx] Login failed (%s)', r.status_code)
    except Exception as exc:
        logger.error('[n8n-sx] Cannot reach n8n: %s', exc)
        _login_fail_until = now_ts + 15
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
        logger.error('[n8n-sx] Request failed %s %s: %s', method, path, exc)
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
            'id': wf.get('id'),
            'name': wf.get('name'),
            'active': wf.get('active', False),
            'nodes': len(wf.get('nodes', [])),
            'updatedAt': wf.get('updatedAt'),
            'createdAt': wf.get('createdAt'),
            'tags': [t.get('name') for t in wf.get('tags', [])],
        })
    return jsonify({'success': True, 'workflows': result})


@n8n_api_bp.route('/api/n8n/workflows/<wf_id>/run', methods=['POST'])
@login_required
def run_workflow(wf_id):
    try:
        return _do_run_workflow(wf_id)
    except Exception as exc:
        logger.error('[n8n-sx] Run failed: %s', exc, exc_info=True)
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
                payload = test_data or {'test': True, 'source': 'ANSER-SanXuat'}
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
            'id': ex.get('id'),
            'status': ex.get('status'),
            'startedAt': ex.get('startedAt'),
            'stoppedAt': ex.get('stoppedAt'),
            'mode': ex.get('mode'),
        })
    return jsonify({'success': True, 'executions': result})


@n8n_api_bp.route('/api/n8n/executions', methods=['GET'])
@login_required
def list_all_executions():
    """Executions across every workflow — powers 'Lịch sử chạy' (real n8n
    run history, replacing the old localStorage sample log)."""
    limit = request.args.get('limit', 30, type=int)

    names = {}
    wf_r = _n8n_get('workflows')
    if wf_r and wf_r.status_code == 200:
        for w in wf_r.json().get('data', []):
            names[w.get('id')] = w.get('name')

    r = _n8n_get(f'executions?limit={limit}')
    if not r or r.status_code != 200:
        return jsonify({'success': False, 'error': 'Cannot reach n8n', 'executions': []}), 502
    execs = r.json().get('data', [])
    result = []
    for ex in execs:
        wf_id = ex.get('workflowId')
        result.append({
            'id': ex.get('id'),
            'workflowId': wf_id,
            'workflowName': names.get(wf_id, wf_id or '—'),
            'status': ex.get('status'),
            'startedAt': ex.get('startedAt'),
            'stoppedAt': ex.get('stoppedAt'),
            'mode': ex.get('mode'),
        })
    return jsonify({'success': True, 'executions': result})


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


# ── Internal callback endpoints ─────────────────────────────────────────────
# Called by the manuf_*.json workflows running inside n8n (not by the browser)
# via RAG_BASE_URL / NOTIFY_URL / BRAIN_BASE_URL, set in docker-compose.yml.
# No @login_required — n8n has no ANSER session cookie.

def _log_event(action, payload):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO automation_events (action, payload, created_at) VALUES (?, ?, ?)',
            (action, json.dumps(payload, ensure_ascii=False, default=str), now()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _internal_material_batch_insert(payload):
    """Mirrors create_material_batch (routes/inventory_routes.py) with
    created_by=None — n8n has no Flask-Login session. See 02.2-CONTEXT.md
    Field-Mapping Fidelity: only material_code/qty_kg/farmer are mapped,
    every other n8n-sent field is silently dropped (lossy-wiring decision).
    """
    material_code = payload.get('material_code')
    material = _find_material(material_code)
    if not material:
        return {'success': False, 'message': 'Mã nguyên vật liệu không hợp lệ'}, 400
    try:
        quantity = float(payload.get('qty_kg') or 0)
    except (TypeError, ValueError):
        quantity = 0
    if quantity <= 0:
        return {'success': False, 'message': 'Số lượng phải lớn hơn 0'}, 400

    conn = get_connection()
    try:
        supplier_id = _resolve_supplier(conn, payload.get('farmer'), None)
        cur = conn.execute(
            'INSERT INTO material_batches (material_code, material_name, unit, supplier_id, '
            'quantity, expiry_date, notes, created_by, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (material['code'], material['name'], material['unit'], supplier_id, quantity,
             '', '', None, now()),
        )
        batch_id = cur.lastrowid
        code = f'LO-{2000 + batch_id}'
        conn.execute('UPDATE material_batches SET code = ? WHERE id = ?', (code, batch_id))
        conn.commit()
        return {'success': True, 'id': batch_id, 'code': code,
                'lot_code': code, 'farmer': payload.get('farmer') or '',
                'material_code': material['code'], 'qty_kg': quantity,
                'status': 'ok'}, 201
    except Exception as e:
        conn.rollback()
        return {'success': False, 'message': str(e)}, 400
    finally:
        conn.close()


# Per-action dispatch for the actions that now have real backing tables
# (02.2-CONTEXT.md Action Routing decision). Every action NOT in this dict
# falls through unchanged to the existing _log_event/automation_events
# catch-all below.
_REAL_TABLE_ACTIONS = {
    'material-batch-insert': _internal_material_batch_insert,
}


@n8n_api_bp.route('/api/n8n/internal/rag/<path:action>', methods=['GET', 'POST'])
def internal_rag(action):
    """Dispatch for {{ $env.RAG_BASE_URL }}/<action> calls.

    Actions with a real backing table (see _REAL_TABLE_ACTIONS) write
    directly to that table. Every other action keeps falling through to
    the generic automation_events sink, unchanged from before this phase.
    """
    payload = request.get_json(silent=True) or dict(request.args)
    handler = _REAL_TABLE_ACTIONS.get(action)
    if handler:
        body, status = handler(payload)
        return jsonify(body), status
    event_id = _log_event(f'rag:{action}', payload)
    return jsonify({'success': True, 'id': event_id, 'action': action, 'received': payload})


@n8n_api_bp.route('/api/n8n/internal/notify', methods=['GET', 'POST'])
def internal_notify():
    """Sink for {{ $env.NOTIFY_URL }} / {{ $env.DOCS_URL }} calls."""
    payload = request.get_json(silent=True) or dict(request.args)
    event_id = _log_event('notify', payload)
    logger.info('[n8n-sx] notify: %s', payload)
    return jsonify({'success': True, 'id': event_id})


@n8n_api_bp.route('/api/n8n/internal/brain/chat', methods=['POST'])
def internal_brain_chat():
    """Mock stub for {{ $env.BRAIN_BASE_URL }}/chat — no real LLM is wired
    up for San Xuat. Clearly flagged as mock so it's obvious in any output."""
    _log_event('brain:chat', request.get_json(silent=True) or {})
    return jsonify({
        'success': True, 'mock': True,
        'message': '[MOCK] Dịch vụ AI/Brain chưa được triển khai cho Sản xuất — đây là phản hồi giả lập.',
    })


@n8n_api_bp.route('/api/n8n/internal/brain/upload', methods=['POST'])
def internal_brain_upload():
    """Mock stub for {{ $env.BRAIN_BASE_URL }}/upload (OCR)."""
    _log_event('brain:upload', dict(request.args))
    return jsonify({'success': True, 'mock': True, 'extracted': {}, 'confidence': 0})


@n8n_api_bp.route('/api/n8n/internal/brain/mcp/validate-invoice', methods=['POST'])
def internal_brain_validate_invoice():
    """Mock stub for {{ $env.BRAIN_BASE_URL }}/mcp/validate-invoice."""
    _log_event('brain:validate-invoice', request.get_json(silent=True) or {})
    return jsonify({'success': True, 'mock': True, 'valid': True})


# n8n's HTTP Request nodes call these with no session/CSRF token — exempt
# them individually (login-required routes above stay CSRF-protected).
csrf.exempt(internal_rag)
csrf.exempt(internal_notify)
csrf.exempt(internal_brain_chat)
csrf.exempt(internal_brain_upload)
csrf.exempt(internal_brain_validate_invoice)


@n8n_api_bp.route('/api/n8n/internal/events', methods=['GET'])
@login_required
def internal_events_list():
    """Browser-facing (auth required) view of automation_events, so the
    Workflows UI can show what n8n actually called back with."""
    limit = request.args.get('limit', 20, type=int)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute('SELECT id, action, payload, created_at FROM automation_events '
                    'ORDER BY id DESC LIMIT ?', (limit,))
        rows = cur.fetchall()
        events = []
        for row in rows:
            d = dict(row)
            try:
                d['payload'] = json.loads(d['payload']) if d['payload'] else None
            except Exception:
                pass
            events.append(d)
        return jsonify({'success': True, 'events': events})
    finally:
        conn.close()


# ── Template API ─────────────────────────────────────────────────────────────

_TEMPLATE_META = {
    'manuf_material_batch_intake': {'icon': 'fa-truck-ramp-box', 'color': '#8D6E63', 'label': 'Nhập lô nguyên liệu', 'desc': 'Webhook nhận phiếu cân → OCR/đối chiếu → lưu lô nguyên liệu'},
    'manuf_lab_test_gate':         {'icon': 'fa-flask-vial',     'color': '#00ACC1', 'label': 'Cổng kiểm định QC',       'desc': 'Webhook nhận kết quả xét nghiệm → lưu kết quả → thông báo'},
    'manuf_generate_material_list':{'icon': 'fa-list-check',     'color': '#7CB342', 'label': 'Tạo danh sách vật tư',    'desc': 'Đơn sản xuất được duyệt → tính nhu cầu vật tư bằng AI → lưu'},
    'manuf_ocr_customer_order':    {'icon': 'fa-file-invoice',   'color': '#5C6BC0', 'label': 'OCR đơn hàng khách',      'desc': 'Webhook nhận ảnh đơn hàng → OCR + xác thực → tạo lệnh sản xuất'},
    'manuf_batch_process_log':     {'icon': 'fa-industry',       'color': '#FB8C00', 'label': 'Nhật ký quy trình lô',    'desc': 'Webhook ghi nhận sự kiện trong quá trình sản xuất theo lô'},
    'manuf_waste_profit_report':   {'icon': 'fa-chart-pie',      'color': '#EF5350', 'label': 'Báo cáo hao hụt & lợi nhuận', 'desc': 'Webhook báo cáo cuối ca → tính hao hụt/lợi nhuận → lưu + thông báo'},
    'manuf_dr_report_periodic':    {'icon': 'fa-file-lines',     'color': '#42A5F5', 'label': 'Báo cáo định kỳ (DR)',    'desc': 'Lịch chạy hàng tháng → tổng hợp báo cáo bằng AI → gửi thông báo'},
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
                'slug': slug,
                'name': wf.get('name', slug),
                'node_count': len(wf.get('nodes', [])),
                'icon': meta.get('icon', 'fa-project-diagram'),
                'color': meta.get('color', '#003152'),
                'label': meta.get('label', wf.get('name', slug)),
                'desc': meta.get('desc', ''),
            })
        except Exception:
            pass
    return jsonify({'success': True, 'templates': templates})


@n8n_api_bp.route('/api/n8n/templates/deploy', methods=['POST'])
@login_required
def deploy_template():
    slug = (request.get_json(silent=True) or {}).get('slug', '')
    fp = os.path.join(_TEMPLATES, f'{slug}.json')
    if not slug or not os.path.isfile(fp):
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    try:
        with open(fp, encoding='utf-8') as f:
            wf = json.load(f)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    _ensure_auth()
    wf_name = wf.get('name', slug)

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
