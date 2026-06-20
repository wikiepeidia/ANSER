"""Transparent reverse-proxy for the local n8n instance.

n8n chạy trong Docker tại localhost:5678 (root path, không có N8N_PATH).
ANSER expose n8n qua /n8n/* — proxy strip prefix /n8n rồi forward.
Các path phụ (/rest/*, /assets/*, /icons/*) cũng được proxy để SPA hoạt động trong iframe.
"""

import os
import secrets
import json
import glob

import requests as _req
from flask import Blueprint, Response, jsonify, redirect, request
from flask_login import login_required

from core.logger import get_logger

logger = get_logger(__name__)

n8n_proxy_bp = Blueprint('n8n_proxy', __name__)

_N8N_ORIGIN  = 'http://localhost:5678'
_CREDS_FILE  = os.path.join(os.path.dirname(__file__), '..', '.n8n_creds.json')
_TEMPLATES   = os.path.join(os.path.dirname(__file__), '..', 'workflow_templates')
_SES         = _req.Session()
_authed      = False
_login_fail_until = 0   # timestamp: skip login retries until this time

_SKIP_REQ = {'host', 'content-length', 'transfer-encoding', 'connection'}
_SKIP_RES = {
    'content-encoding', 'content-length', 'transfer-encoding', 'connection',
    'x-frame-options', 'content-security-policy', 'strict-transport-security',
}

# n8n's internal paths that the SPA JS calls (without /n8n prefix)
_N8N_INTERNAL_PREFIXES = ('rest', 'assets', 'icons', 'push', 'webhook',
                          'webhook-test', 'form', 'canvas')


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
        logger.error('[n8n proxy] Cannot save credentials: %s', e)


def _get_creds():
    """Env vars take priority, then saved file."""
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
    """Return True if n8n owner account has not been created yet."""
    try:
        r = _req.get(f'{_N8N_ORIGIN}/rest/settings', timeout=5)
        if r.status_code == 200:
            data = r.json().get('data', {})
            um = data.get('userManagement', {})
            if 'showSetupOnFirstLoad' in um:
                return um['showSetupOnFirstLoad']
            return not um.get('isInstanceOwnerSetUp', True)
    except Exception:
        pass
    return False


def _auto_setup():
    """Create n8n owner account automatically and save credentials."""
    saved = _load_creds()
    if saved:
        return saved['email'], saved['password']

    email    = 'admin@anser.local'
    password = secrets.token_urlsafe(16)

    try:
        r = _req.post(
            f'{_N8N_ORIGIN}/rest/owner/setup',
            json={
                'email':     email,
                'password':  password,
                'firstName': 'ANSER',
                'lastName':  'Admin',
            },
            timeout=10,
        )
        if r.status_code in (200, 201):
            _save_creds(email, password)
            logger.info('[n8n proxy] Auto-setup complete: %s', email)
            return email, password
        logger.error('[n8n proxy] Setup failed %s: %s', r.status_code, r.text[:200])
    except Exception as e:
        logger.error('[n8n proxy] Setup error: %s', e)

    return '', ''


# ── Auth ─────────────────────────────────────────────────────────────────────

def _login():
    global _authed, _login_fail_until
    import time

    now = time.time()
    if now < _login_fail_until:
        return False

    try:
        if _needs_setup():
            logger.info('[n8n proxy] First run — running auto-setup...')
            _auto_setup()
    except Exception:
        pass

    email, pwd = _get_creds()
    if not email or not pwd:
        logger.warning('[n8n proxy] No credentials found. '
                       'Set N8N_ADMIN_EMAIL / N8N_ADMIN_PASSWORD in .env')
        _login_fail_until = now + 60
        return False

    try:
        r = _SES.post(
            f'{_N8N_ORIGIN}/rest/login',
            json={'emailOrLdapLoginId': email, 'password': pwd},
            timeout=5,
        )
        _authed = r.status_code == 200
        if _authed:
            logger.info('[n8n proxy] Authenticated as %s', email)
            _login_fail_until = 0
        else:
            logger.warning('[n8n proxy] Login failed (%s) for %s', r.status_code, email)
            _login_fail_until = now + 30
    except Exception as exc:
        logger.error('[n8n proxy] Cannot reach n8n: %s', exc)
        _authed = False
        _login_fail_until = now + 15

    return _authed


def _ensure_auth():
    if not _authed:
        _login()


# ── Core proxy logic ─────────────────────────────────────────────────────────

def _proxy_to_n8n(upstream_path):
    """Forward a request to n8n and return the response."""
    global _authed

    _ensure_auth()

    url = f'{_N8N_ORIGIN}/{upstream_path}'
    if request.query_string:
        url += '?' + request.query_string.decode('utf-8', errors='replace')

    fwd_headers = {k: v for k, v in request.headers if k.lower() not in _SKIP_REQ}

    def _call():
        return _SES.request(
            method=request.method,
            url=url,
            headers=fwd_headers,
            data=request.get_data(),
            allow_redirects=False,
            timeout=30,
        )

    try:
        up = _call()
    except Exception as exc:
        return Response(f'[ANSER] n8n unavailable: {exc}',
                        status=502, content_type='text/plain')

    # Re-auth once on 401
    if up.status_code == 401:
        _authed = False
        if _login():
            try:
                up = _call()
            except Exception as exc:
                return Response(f'[ANSER] n8n unavailable: {exc}',
                                status=502, content_type='text/plain')

    # Rewrite redirects
    if up.status_code in (301, 302, 303, 307, 308):
        loc = up.headers.get('Location', '')
        if loc.startswith(_N8N_ORIGIN):
            loc = loc[len(_N8N_ORIGIN):]
        if loc.startswith('/') and not loc.startswith('/n8n'):
            loc = '/n8n' + loc
        return redirect(loc, code=up.status_code)

    content_type = up.headers.get('Content-Type', 'application/octet-stream')
    content = up.content

    # Rewrite HTML: add /n8n prefix to absolute paths so assets load through proxy
    if 'text/html' in content_type:
        content = _rewrite_html(content)

    res_headers = {k: v for k, v in up.headers.items() if k.lower() not in _SKIP_RES}

    return Response(content, status=up.status_code,
                    headers=res_headers, content_type=content_type)


def _rewrite_html(content: bytes) -> bytes:
    """Rewrite absolute paths in HTML so they go through /n8n/ proxy."""
    content = content.replace(b'src="/', b'src="/n8n/')
    content = content.replace(b'href="/', b'href="/n8n/')
    content = content.replace(b"src='/", b"src='/n8n/")
    content = content.replace(b"href='/", b"href='/n8n/")
    # Fix double-prefix
    content = content.replace(b'="/n8n/n8n/', b'="/n8n/')
    content = content.replace(b"='/n8n/n8n/", b"='/n8n/")
    # Fix protocol-relative URLs that got wrongly prefixed
    content = content.replace(b'="/n8n//', b'="//')
    content = content.replace(b"='/n8n//", b"='//")
    return content


# ── Template metadata ────────────────────────────────────────────────────────

_TEMPLATE_META = {
    'iot_pos_demo':         {'icon': 'fa-cash-register',  'color': '#FF6B35', 'label': 'POS → NeonDB → Discord',     'desc': 'Nhận sự kiện POS, lưu DB, thông báo Discord'},
    'daily_sales_report':   {'icon': 'fa-chart-bar',      'color': '#306699', 'label': 'Báo cáo doanh số hàng ngày', 'desc': 'Mỗi 20h tổng hợp sales → Discord embed'},
    'low_stock_alert':      {'icon': 'fa-boxes',          'color': '#FF9800', 'label': 'Cảnh báo tồn kho thấp',      'desc': 'Mỗi 6h check stock < 10 → Discord cảnh báo'},
    'new_customer_welcome': {'icon': 'fa-user-plus',      'color': '#34A700', 'label': 'Khách hàng mới → Welcome',   'desc': 'Webhook nhận KH mới → NeonDB → Discord'},
    'ai_security_analyzer': {'icon': 'fa-shield-alt',     'color': '#E91E63', 'label': 'AI Security Log Analyzer',   'desc': 'Phân tích log bảo mật bằng LLM + RAG'},
    'iot_events_ingest':    {'icon': 'fa-satellite-dish',  'color': '#009688', 'label': 'IoT Events Ingest',          'desc': 'Webhook nhận IoT event → NeonDB'},
}


# ── Template API ─────────────────────────────────────────────────────────────

@n8n_proxy_bp.route('/api/n8n-templates', methods=['GET'])
@login_required
def list_templates():
    """List available workflow templates with metadata."""
    templates = []
    for fp in sorted(glob.glob(os.path.join(_TEMPLATES, '*.json'))):
        slug = os.path.splitext(os.path.basename(fp))[0]
        meta = _TEMPLATE_META.get(slug, {})
        try:
            with open(fp, encoding='utf-8') as f:
                wf = json.load(f)
            templates.append({
                'slug':      slug,
                'name':      wf.get('name', slug),
                'node_count': len(wf.get('nodes', [])),
                'icon':      meta.get('icon', 'fa-project-diagram'),
                'color':     meta.get('color', '#667eea'),
                'label':     meta.get('label', wf.get('name', slug)),
                'desc':      meta.get('desc', ''),
            })
        except Exception:
            pass
    return jsonify({'success': True, 'templates': templates})


@n8n_proxy_bp.route('/api/n8n-templates/deploy', methods=['POST'])
@login_required
def deploy_template():
    """Import a workflow template into n8n."""
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

    # Check if already imported
    try:
        r = _SES.get(f'{_N8N_ORIGIN}/rest/workflows', timeout=10)
        if r.status_code == 200:
            for w in r.json().get('data', []):
                if w.get('name') == wf_name:
                    return jsonify({'success': True, 'message': 'Đã tồn tại',
                                    'id': w['id'], 'existing': True})
    except Exception:
        pass

    # Import
    try:
        r = _SES.post(
            f'{_N8N_ORIGIN}/rest/workflows',
            json=wf,
            headers={'Content-Type': 'application/json'},
            timeout=15,
        )
        if r.status_code in (200, 201):
            data = r.json().get('data', {})
            return jsonify({'success': True, 'message': 'Import thành công!',
                            'id': data.get('id'), 'name': wf_name})
        return jsonify({'success': False,
                        'error': f'n8n trả {r.status_code}: {r.text[:200]}'}), 502
    except Exception as exc:
        return jsonify({'success': False, 'error': str(exc)}), 502


# ── Strip Talisman iframe-blocking headers ───────────────────────────────────

@n8n_proxy_bp.after_request
def allow_iframe(response):
    """Remove headers that prevent embedding proxy content in ANSER's iframe."""
    response.headers.pop('X-Frame-Options', None)
    csp = response.headers.get('Content-Security-Policy', '')
    if 'frame-ancestors' in csp:
        parts = [p.strip() for p in csp.split(';') if 'frame-ancestors' not in p]
        if parts:
            response.headers['Content-Security-Policy'] = '; '.join(parts)
        else:
            response.headers.pop('Content-Security-Policy', None)
    return response


# ── Proxy routes ──────────────────────────────────────────────────────────────

@n8n_proxy_bp.route('/n8n', methods=['GET'])
@login_required
def n8n_root():
    return redirect('/n8n/workflows')


@n8n_proxy_bp.route('/n8n/', defaults={'path': ''})
@n8n_proxy_bp.route('/n8n/<path:path>',
                    methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
@login_required
def proxy(path):
    """Main proxy: /n8n/xxx → localhost:5678/xxx (strip /n8n prefix)."""
    # Override base-path.js so n8n JS uses /n8n/ prefix for ALL API calls
    if path == 'static/base-path.js':
        return Response(
            "window.BASE_PATH = '/n8n/';",
            content_type='application/javascript',
        )
    return _proxy_to_n8n(path)
