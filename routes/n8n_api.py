"""n8n API integration — ANSER gọi n8n REST API, không dùng proxy/iframe."""

import os
import secrets
import json
import glob
from datetime import datetime
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


# ── Credential auto-provisioning ────────────────────────────────────────────

_SMTP_CRED_NAME = 'ANSER SMTP'


def _ensure_smtp_credential():
    """Return the id of the shared SMTP credential, creating it from
    Config.SMTP_* on first use. Mirrors _auto_setup()'s "no manual n8n UI
    clicking required" approach — deploy_template() calls this whenever a
    template needs an emailSend node wired up."""
    r = _n8n_get('credentials')
    if r and r.status_code == 200:
        for c in r.json().get('data', []):
            if c.get('name') == _SMTP_CRED_NAME and c.get('type') == 'smtp':
                return c['id']
    payload = {
        'name': _SMTP_CRED_NAME,
        'type': 'smtp',
        'data': {
            'user': Config.SMTP_USER,
            'password': Config.SMTP_PASS,
            'host': Config.N8N_SMTP_HOST,
            'port': Config.SMTP_PORT,
            'secure': Config.N8N_SMTP_SECURE,
        },
    }
    r = _n8n_post('credentials', data=payload)
    if r and r.status_code in (200, 201):
        return r.json().get('data', {}).get('id')
    logger.error('[n8n] Failed to create SMTP credential: %s',
                 r.text[:200] if r else 'no response')
    return None


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


@n8n_api_bp.route('/api/n8n/internal/iot-events', methods=['POST'])
def internal_iot_events_insert():
    """Internal endpoint for n8n workflows — no auth required.

    Replaces the old rag-service call (that service no longer exists —
    lived in a separate demo project, was never part of this app's own
    docker-compose). Used by iot_pos_demo.json's webhook to persist the
    event it just received before formatting a notification from it.
    """
    from flask import current_app
    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available'}), 503
    data = request.get_json(silent=True) or {}
    device_id = (data.get('device_id') or '').strip()
    event_type = (data.get('event_type') or '').strip()
    payload = data.get('payload') or {}
    if not device_id or not event_type:
        return jsonify({'success': False, 'error': 'device_id and event_type are required'}), 400
    try:
        conn = db.get_business_connection()
        cursor = conn.cursor()
        if db.use_postgres:
            cursor.execute(
                'INSERT INTO iot_events (device_id, event_type, payload) VALUES (%s, %s, %s) '
                'RETURNING id, created_at',
                (device_id, event_type, json.dumps(payload)),
            )
        else:
            cursor.execute(
                'INSERT INTO iot_events (device_id, event_type, payload) VALUES (?, ?, ?)',
                (device_id, event_type, json.dumps(payload)),
            )
        row = cursor.fetchone() if db.use_postgres else None
        conn.commit()
        result_id = row['id'] if row else cursor.lastrowid
        created_at = row['created_at'].isoformat() if row and hasattr(row['created_at'], 'isoformat') else None
        conn.close()
        return jsonify({'success': True, 'id': result_id, 'created_at': created_at}), 201
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500


@n8n_api_bp.route('/api/n8n/internal/customers', methods=['POST'])
def internal_customers_insert():
    """Internal endpoint for n8n workflows — no auth required.

    Replaces the old rag-service call for new_customer_welcome.json.
    Delegates to the same create_customer() the authenticated /api/customers
    route uses, generating a code if the caller didn't supply one.
    """
    from flask import current_app
    from core.services.customer_service import create_customer
    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available'}), 503
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'name is required'}), 400
    code = (data.get('code') or '').strip() or f'C-{secrets.token_hex(4).upper()}'
    conn = db.get_business_connection()
    try:
        ok, error = create_customer(
            conn, code, name,
            data.get('phone'), data.get('email'), data.get('address'), data.get('notes'),
            created_by=None,
        )
        if not ok:
            return jsonify({'success': False, 'error': error}), 409
        return jsonify({'success': True, 'code': code, 'name': name}), 201
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 500
    finally:
        conn.close()


@n8n_api_bp.route('/api/n8n/internal/warehouses', methods=['GET'])
def internal_warehouses():
    """Internal endpoint for n8n workflows — no auth required.

    Returns active warehouse alert profiles (threshold + Discord webhook +
    notification email) for the low_stock_alert workflow to loop over.
    """
    from flask import current_app
    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available', 'warehouses': []})
    try:
        conn = db.get_business_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, low_stock_threshold, discord_webhook_url, notification_email '
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


@n8n_api_bp.route('/api/n8n/internal/daily-sales', methods=['GET'])
def internal_daily_sales():
    """Internal endpoint for n8n workflows — no auth required.

    Replaces the old rag-service call (that service no longer exists — it
    lived in a separate demo project, was never part of this app's own
    docker-compose, so daily_sales_report.json 404'd on every real run).
    Computes the same summary directly from this app's own `sales` table.

    Default is a single day (?date=YYYY-MM-DD, defaults to today) — pass
    ?days=N instead for an N-day lookback window ending today (used by
    weekly_sales_report.json/monthly_sales_report.json with days=7/30) so
    those reuse this same aggregation instead of forking a near-duplicate.
    """
    from flask import current_app
    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available'})
    days = request.args.get('days', type=int)
    date_str = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    try:
        conn = db.get_business_connection()
        cursor = conn.cursor()
        if days:
            if db.use_postgres:
                where_clause = "created_at::date BETWEEN (CURRENT_DATE - %s * INTERVAL '1 day') AND CURRENT_DATE"
                where_params = (days,)
            else:
                where_clause = "date(created_at) BETWEEN date('now', ?) AND date('now')"
                where_params = (f'-{days} days',)
        else:
            if db.use_postgres:
                where_clause = 'created_at::date = %s::date'
            else:
                where_clause = 'date(created_at) = date(?)'
            where_params = (date_str,)

        cursor.execute(
            'SELECT COUNT(*) AS total_orders, COALESCE(SUM(total_amount), 0) AS total_revenue,'
            f' COUNT(DISTINCT user_id) AS unique_staff FROM sales WHERE {where_clause}', where_params
        )
        row = cursor.fetchone()
        summary = dict(row) if hasattr(row, 'keys') else dict(zip([d[0] for d in cursor.description], row))
        summary['total_revenue'] = float(summary['total_revenue'] or 0)

        cursor.execute(
            f'SELECT items FROM sales WHERE {where_clause} AND items IS NOT NULL', where_params
        )
        totals = {}
        for r in cursor.fetchall():
            raw = r['items'] if hasattr(r, 'keys') else r[0]
            try:
                items = json.loads(raw) if isinstance(raw, str) else (raw or [])
            except Exception:
                items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = item.get('name', 'N/A')
                qty = int(item.get('qty', 0) or 0)
                price = float(item.get('price', 0) or 0)
                agg = totals.setdefault(name, {'product_name': name, 'qty_sold': 0, 'revenue': 0.0})
                agg['qty_sold'] += qty
                agg['revenue'] += qty * price
        top_products = sorted(totals.values(), key=lambda x: x['revenue'], reverse=True)[:5]

        conn.close()
        period = f'{days} ngày qua' if days else date_str
        return jsonify({'success': True, 'date': date_str, 'period': period, 'days': days, 'summary': summary, 'top_products': top_products})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)})


@n8n_api_bp.route('/api/n8n/internal/expiring-products', methods=['GET'])
def internal_expiring_products():
    """Internal endpoint for n8n workflows — no auth required.

    Products with expiry_date set (nullable — most won't have one) that
    falls within the next N days. Backs product_expiry_alert.json.
    """
    from flask import current_app
    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available', 'items': []})
    days = request.args.get('days', 7, type=int)
    try:
        conn = db.get_business_connection()
        cursor = conn.cursor()
        if db.use_postgres:
            cursor.execute(
                "SELECT name, code, stock_quantity, expiry_date FROM products "
                "WHERE expiry_date IS NOT NULL AND expiry_date != '' "
                "AND expiry_date::date BETWEEN CURRENT_DATE AND (CURRENT_DATE + %s * INTERVAL '1 day') "
                "ORDER BY expiry_date ASC",
                (days,),
            )
        else:
            cursor.execute(
                "SELECT name, code, stock_quantity, expiry_date FROM products "
                "WHERE expiry_date IS NOT NULL AND expiry_date != '' "
                "AND date(expiry_date) BETWEEN date('now') AND date('now', ?) "
                "ORDER BY expiry_date ASC",
                (f'+{days} days',),
            )
        rows = cursor.fetchall()
        items = [
            dict(r) if hasattr(r, 'keys') else dict(zip([d[0] for d in cursor.description], r))
            for r in rows
        ]
        conn.close()
        return jsonify({'success': True, 'threshold_days': days, 'count': len(items), 'items': items})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc), 'items': []})


@n8n_api_bp.route('/api/n8n/internal/expiring-subscriptions', methods=['GET'])
def internal_expiring_subscriptions():
    """Internal endpoint for n8n workflows — no auth required.

    manager_subscriptions (business DB) has no email column — users (auth
    DB) does. Postgres doesn't support cross-database JOINs even within the
    same Neon project, so this does two queries and merges in Python,
    matching core/services/subscription_service.py's established pattern
    for the exact same DB split.
    """
    from flask import current_app
    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available', 'subscriptions': []})
    days = request.args.get('days', 7, type=int)
    try:
        conn = db.get_business_connection()
        cursor = conn.cursor()
        if db.use_postgres:
            cursor.execute(
                "SELECT user_id, subscription_type, end_date FROM manager_subscriptions "
                "WHERE status = 'active' AND end_date::date BETWEEN CURRENT_DATE AND (CURRENT_DATE + %s * INTERVAL '1 day')",
                (days,),
            )
        else:
            cursor.execute(
                "SELECT user_id, subscription_type, end_date FROM manager_subscriptions "
                "WHERE status = 'active' AND date(end_date) BETWEEN date('now') AND date('now', ?)",
                (f'+{days} days',),
            )
        rows = [dict(r) if hasattr(r, 'keys') else dict(zip([d[0] for d in cursor.description], r))
                for r in cursor.fetchall()]
        conn.close()

        user_ids = [r['user_id'] for r in rows]
        emails = {}
        if user_ids:
            auth_conn = db.get_connection()
            ac = auth_conn.cursor()
            ph = ', '.join(['%s'] * len(user_ids)) if db.use_postgres else ', '.join(['?'] * len(user_ids))
            ac.execute(f'SELECT id, name, email FROM users WHERE id IN ({ph})', user_ids)
            for u in ac.fetchall():
                u = dict(u) if hasattr(u, 'keys') else dict(zip([d[0] for d in ac.description], u))
                # manager_subscriptions.user_id is TEXT in production (predates
                # Alembic, same drift as scheduled_reports.id/iot_events —
                # see migration 006's docstring) while users.id is a real
                # INTEGER; str() both sides so the lookup below actually matches
                # instead of silently finding nothing.
                emails[str(u['id'])] = u
            auth_conn.close()

        subs = []
        for r in rows:
            u = emails.get(str(r['user_id']))
            if not u or not u.get('email'):
                continue
            end_date = r['end_date']
            subs.append({
                'user_email': u['email'],
                'user_name': u.get('name') or u['email'],
                'subscription_type': r['subscription_type'],
                'end_date': end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date,
            })
        return jsonify({'success': True, 'subscriptions': subs, 'count': len(subs)})
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc), 'subscriptions': []})


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
    'iot_pos_demo':                 {'icon': 'fa-cash-register', 'color': '#FF6B35', 'label': 'POS → NeonDB → Email',       'desc': 'Nhận sự kiện POS, lưu DB, thông báo Email'},
    'daily_sales_report':           {'icon': 'fa-chart-bar',     'color': '#306699', 'label': 'Báo cáo doanh số hàng ngày', 'desc': 'Mỗi ngày tổng hợp sales → Email cho các kho'},
    'weekly_sales_report':          {'icon': 'fa-chart-line',    'color': '#2E7D32', 'label': 'Báo cáo doanh số hàng tuần', 'desc': 'Mỗi 7 ngày tổng hợp sales → Email cho các kho'},
    'monthly_sales_report':         {'icon': 'fa-calendar-alt',  'color': '#6A1B9A', 'label': 'Báo cáo doanh số hàng tháng','desc': 'Mỗi 30 ngày tổng hợp sales → Email cho các kho'},
    'low_stock_alert':              {'icon': 'fa-boxes',         'color': '#FF9800', 'label': 'Cảnh báo tồn kho thấp',      'desc': 'Mỗi 6h check stock thấp → Email cảnh báo'},
    'product_expiry_alert':         {'icon': 'fa-hourglass-half','color': '#D32F2F', 'label': 'Cảnh báo hết hạn sử dụng',   'desc': 'Mỗi ngày check sản phẩm sắp hết hạn → Email'},
    'unusual_transaction_alert':    {'icon': 'fa-exclamation-triangle', 'color': '#C62828', 'label': 'Cảnh báo giao dịch bất thường', 'desc': 'Giao dịch bất thường (đối chiếu trung bình) → Email'},
    'subscription_renewal_reminder':{'icon': 'fa-bell',          'color': '#F57F17', 'label': 'Nhắc gia hạn gói dịch vụ',   'desc': 'Mỗi ngày check gói sắp hết hạn → Email cho chủ tài khoản'},
    'new_customer_welcome':         {'icon': 'fa-user-plus',     'color': '#34A700', 'label': 'Khách hàng mới → Welcome',   'desc': 'Tự động khi thêm khách hàng mới → Email'},
    'order_discord_notify':         {'icon': 'fa-shopping-cart', 'color': '#4CAF50', 'label': 'Đơn hàng → Email',          'desc': 'Nhập/xuất kho → tự động gửi email'},
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


_DAILY_REPORT_WF_NAME = 'Báo cáo doanh số hàng ngày'
_DAILY_REPORT_TRIGGER_NODE = 'Mỗi ngày 20h'

# Same "configurable send hour" pattern for weekly/monthly — settings key ->
# (workflow name, schedule trigger node name, days between runs). daily's
# entry has days_interval=None since its trigger is hours-based (every 24h)
# rather than days-based.
_REPORT_SCHEDULES = {
    'daily_report_hour':   (_DAILY_REPORT_WF_NAME, _DAILY_REPORT_TRIGGER_NODE, None),
    'weekly_report_hour':  ('Báo cáo doanh số hàng tuần', 'Mỗi 7 ngày', 7),
    'monthly_report_hour': ('Báo cáo doanh số hàng tháng', 'Mỗi 30 ngày', 30),
}


def _build_schedule_params(days_interval, hour):
    if days_interval:
        return {'rule': {'interval': [{'field': 'days', 'daysInterval': days_interval, 'triggerAtHour': hour}]}}
    return {'rule': {'interval': [{'field': 'hours', 'hoursInterval': 24, 'triggerAtHour': hour}]}}


def _get_report_hour(setting_key, default=20):
    """Read a `*_report_hour` system_settings value (see /settings' system
    section) — falls back to the template's own default (20) if unset or
    unparseable."""
    from flask import current_app
    db = current_app.extensions.get('database')
    if not db:
        return default
    try:
        conn = db.get_business_connection()
        c = conn.cursor()
        c.execute("SELECT value FROM system_settings WHERE key = ?", (setting_key,))
        row = c.fetchone()
        conn.close()
        return int(row['value']) if row and row['value'] not in (None, '') else default
    except Exception:
        return default


def _get_daily_report_hour():
    return _get_report_hour('daily_report_hour')


def sync_report_hour(setting_key, hour):
    """Push a new send-hour to an already-deployed report workflow's
    schedule trigger, if one exists — called both at deploy time and
    whenever /settings' daily/weekly/monthly_report_hour value is saved, so
    changing it takes effect immediately without redeploying.

    Deactivates before patching and reactivates after: n8n only re-registers
    a schedule trigger's timer on activation, not on a live PATCH while the
    workflow is already active — patching in place silently keeps running
    the old schedule until the next manual toggle (found by force-testing
    weekly/monthly's schedule this same way and watching it keep firing on
    the old interval after a plain PATCH)."""
    cfg = _REPORT_SCHEDULES.get(setting_key)
    if not cfg:
        return False
    wf_name, trigger_node, days_interval = cfg
    try:
        hour = max(0, min(23, int(hour)))
    except (TypeError, ValueError):
        return False
    _ensure_auth()
    r = _n8n_get('workflows')
    if not r or r.status_code != 200:
        return False
    for w in r.json().get('data', []):
        if w.get('name') != wf_name:
            continue
        wid = w['id']
        wf = _n8n_get(f'workflows/{wid}').json().get('data', {})
        nodes = wf.get('nodes', [])
        changed = False
        for n in nodes:
            if n.get('name') == trigger_node:
                n['parameters'] = _build_schedule_params(days_interval, hour)
                changed = True
        if not changed:
            return False
        was_active = wf.get('active', False)
        if was_active:
            _n8n_post(f'workflows/{wid}/deactivate')
        _n8n_patch(f'workflows/{wid}', data={
            'nodes': nodes, 'connections': wf.get('connections', {}),
            'settings': wf.get('settings', {}), 'name': wf.get('name'),
        })
        if was_active:
            vid = _n8n_get(f'workflows/{wid}').json().get('data', {}).get('versionId')
            _n8n_post(f'workflows/{wid}/activate', data={'versionId': vid})
        return True
    return False


def sync_daily_report_hour(hour):
    return sync_report_hour('daily_report_hour', hour)


@n8n_api_bp.route('/api/n8n/templates/deploy', methods=['POST'])
@login_required
def deploy_template():
    slug = (request.get_json(silent=True) or {}).get('slug', '')
    fp   = os.path.join(_TEMPLATES, f'{slug}.json')
    if not slug or not os.path.isfile(fp):
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    try:
        with open(fp, encoding='utf-8') as f:
            raw = f.read()
        # Templates hardcode the local-dev callback address (see
        # Config.ANSER_APP_ORIGIN) — swap it for the real one before this
        # ever reaches n8n, so a production n8n instance calls back into
        # this app correctly instead of a Docker-Desktop-only hostname.
        raw = raw.replace('http://host.docker.internal:5002', Config.ANSER_APP_ORIGIN)
        # Templates hardcode a placeholder From address ("alerts@anser.local",
        # a domain nobody owns — no SPF/DKIM possible, real providers may
        # spam-filter it) instead of reading Config.SMTP_FROM, so switching
        # SMTP_FROM in .env silently had no effect on what recipients saw.
        raw = raw.replace('alerts@anser.local', Config.SMTP_FROM)
        wf = json.loads(raw)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    _ensure_auth()
    wf_name = wf.get('name', slug)

    # Wire up SMTP credentials for any Send Email node — created on first
    # use so the template JSON never has to hardcode a credential id.
    cred_id = None
    for node in wf.get('nodes', []):
        if node.get('type') == 'n8n-nodes-base.emailSend':
            if cred_id is None:
                cred_id = _ensure_smtp_credential()
            if cred_id:
                node['credentials'] = {'smtp': {'id': cred_id, 'name': _SMTP_CRED_NAME}}

    # daily/weekly/monthly_sales_report's send hour is configurable
    # (/settings, system section) rather than fixed at the template's own
    # default (20h).
    _SLUG_TO_SETTING = {
        'daily_sales_report': 'daily_report_hour',
        'weekly_sales_report': 'weekly_report_hour',
        'monthly_sales_report': 'monthly_report_hour',
    }
    if slug in _SLUG_TO_SETTING:
        setting_key = _SLUG_TO_SETTING[slug]
        _, trigger_node, days_interval = _REPORT_SCHEDULES[setting_key]
        hour = _get_report_hour(setting_key)
        for node in wf.get('nodes', []):
            if node.get('name') == trigger_node:
                node['parameters'] = _build_schedule_params(days_interval, hour)

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
