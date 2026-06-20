"""Transparent reverse-proxy for the local n8n instance.

n8n chạy với N8N_PATH=/n8n/ nên serve tại localhost:5678/n8n/.
ANSER expose n8n qua /n8n/* và tự động setup + login (không cần user nhập credential).
"""

import os
import secrets
import json

import requests as _req
from flask import Blueprint, Response, redirect, request
from flask_login import login_required

from core.logger import get_logger

logger = get_logger(__name__)

n8n_proxy_bp = Blueprint('n8n_proxy', __name__)

_N8N_ORIGIN  = 'http://localhost:5678'
_N8N_PREFIX  = '/n8n'               # n8n được start với N8N_PATH=/n8n/
_CREDS_FILE  = os.path.join(os.path.dirname(__file__), '..', '.n8n_creds.json')
_SES         = _req.Session()
_authed      = False

_SKIP_REQ = {'host', 'content-length', 'transfer-encoding', 'connection'}
_SKIP_RES = {
    'content-encoding', 'content-length', 'transfer-encoding', 'connection',
    'x-frame-options', 'content-security-policy', 'strict-transport-security',
}


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
        r = _req.get(f'{_N8N_ORIGIN}{_N8N_PREFIX}/rest/settings', timeout=5)
        if r.status_code == 200:
            um = r.json().get('data', {}).get('userManagement', {})
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
            f'{_N8N_ORIGIN}{_N8N_PREFIX}/rest/owner/setup',
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
    global _authed

    try:
        if _needs_setup():
            logger.info('[n8n proxy] First run — running auto-setup...')
            _auto_setup()
    except Exception:
        pass

    email, pwd = _get_creds()
    if not email or not pwd:
        logger.warning('[n8n proxy] No credentials found. '
                       'Set N8N_ADMIN_EMAIL / N8N_ADMIN_PASSWORD env vars '
                       'or run n8n setup first.')
        return False

    try:
        r = _SES.post(
            f'{_N8N_ORIGIN}{_N8N_PREFIX}/rest/login',
            json={'emailOrLdapLoginId': email, 'password': pwd},
            timeout=5,
        )
        _authed = r.status_code == 200
        if _authed:
            logger.info('[n8n proxy] Authenticated as %s', email)
        else:
            logger.warning('[n8n proxy] Login failed (%s) for %s', r.status_code, email)
    except Exception as exc:
        logger.error('[n8n proxy] Cannot reach n8n: %s', exc)
        _authed = False

    return _authed


def _ensure_auth():
    if not _authed:
        _login()


# ── Routes ────────────────────────────────────────────────────────────────────

@n8n_proxy_bp.route('/n8n', methods=['GET'])
@login_required
def n8n_root():
    return redirect('/n8n/workflows')


@n8n_proxy_bp.route('/n8n/', defaults={'path': ''})
@n8n_proxy_bp.route('/n8n/<path:path>',
                    methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
@login_required
def proxy(path):
    global _authed

    _ensure_auth()

    # Forward WITH /n8n prefix because n8n runs with N8N_PATH=/n8n/
    upstream_path = f'{_N8N_PREFIX}/{path}' if path else f'{_N8N_PREFIX}/'
    url = f'{_N8N_ORIGIN}{upstream_path}'
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

    # Re-auth once if n8n returned 401
    if up.status_code == 401:
        _authed = False
        if _login():
            try:
                up = _call()
            except Exception as exc:
                return Response(f'[ANSER] n8n unavailable: {exc}',
                                status=502, content_type='text/plain')

    # Rewrite redirect Location headers from absolute n8n URLs → proxy URLs
    if up.status_code in (301, 302, 303, 307, 308):
        loc = up.headers.get('Location', '')
        if loc.startswith(_N8N_ORIGIN):
            loc = loc[len(_N8N_ORIGIN):]       # strip origin, keep path
        # loc is now e.g. /n8n/workflows — already has /n8n prefix, passthrough
        return redirect(loc, code=up.status_code)

    res_headers = {k: v for k, v in up.headers.items() if k.lower() not in _SKIP_RES}

    return Response(
        up.content,
        status=up.status_code,
        headers=res_headers,
        content_type=up.headers.get('Content-Type', 'application/octet-stream'),
    )
