"""Lightweight reverse-proxy for n8n editor iframe.

Dùng chung auth token từ n8n_api module.
Chỉ phục vụ iframe editor trong ANSER — không dùng cho API calls.
"""

import threading
import requests as _req
from flask import Blueprint, Response, redirect, request
from flask_login import login_required
from flask_sock import Sock

n8n_proxy_bp = Blueprint('n8n_proxy', __name__)
_n8n_sock = Sock()

_N8N_ORIGIN = 'http://localhost:5678'
_ASSET_CACHE = {}
_SKIP_RES = {
    'content-encoding', 'content-length', 'transfer-encoding', 'connection',
    'x-frame-options', 'content-security-policy', 'strict-transport-security',
}


def _get_token():
    from routes.n8n_api import _ensure_auth
    _ensure_auth()
    from routes.n8n_api import _auth_token as token
    return token


def init_websocket(app):
    _n8n_sock.init_app(app)


def _proxy(upstream_path):
    is_static = upstream_path.startswith(('assets/', 'static/'))
    if is_static and upstream_path in _ASSET_CACHE:
        content, ct = _ASSET_CACHE[upstream_path]
        return Response(content, content_type=ct,
                        headers={'Cache-Control': 'public, max-age=31536000'})

    token = _get_token()
    url = f'{_N8N_ORIGIN}/{upstream_path}'
    if request.query_string:
        url += '?' + request.query_string.decode('utf-8', errors='replace')

    _FWD = {'content-type', 'accept', 'origin', 'referer', 'x-requested-with',
            'browser-id', 'push-ref'}
    headers = {k: v for k, v in request.headers if k.lower() in _FWD}
    if token:
        headers['Cookie'] = f'n8n-auth={token}'

    try:
        r = _req.request(
            method=request.method, url=url, headers=headers,
            data=request.get_data(), allow_redirects=False, timeout=30,
        )
    except Exception as exc:
        return Response(f'n8n unavailable: {exc}', status=502, content_type='text/plain')

    if r.status_code in (301, 302, 303, 307, 308):
        loc = r.headers.get('Location', '')
        if loc.startswith(_N8N_ORIGIN):
            loc = loc[len(_N8N_ORIGIN):]
        if loc.startswith('/') and not loc.startswith('/n8n'):
            loc = '/n8n' + loc
        return redirect(loc, code=r.status_code)

    content = r.content
    content_type = r.headers.get('Content-Type', 'application/octet-stream')

    if 'text/html' in content_type:
        content = content.replace(b'src="/', b'src="/n8n/')
        content = content.replace(b'href="/', b'href="/n8n/')
        content = content.replace(b"src='/", b"src='/n8n/")
        content = content.replace(b"href='/", b"href='/n8n/")
        content = content.replace(b'="/n8n/n8n/', b'="/n8n/')
        content = content.replace(b"='/n8n/n8n/", b"='/n8n/")
        content = content.replace(b'="/n8n//', b'="//')
        content = content.replace(b"='/n8n//", b"='//")
        content = content.replace(
            b'</head>',
            b'<link rel="stylesheet" href="/static/css/n8n_override.css">'
            b'<script src="/static/js/n8n_vi.js" defer></script></head>',
        )
        content = content.replace(b'<title>n8n', b'<title>ANSER')
        content = content.replace(b'<title>Workflow', b'<title>ANSER - Workflow')

    if is_static and r.status_code == 200:
        _ASSET_CACHE[upstream_path] = (content, content_type)

    res_headers = {k: v for k, v in r.headers.items() if k.lower() not in _SKIP_RES}
    if is_static:
        res_headers['Cache-Control'] = 'public, max-age=31536000'
    return Response(content, status=r.status_code, headers=res_headers,
                    content_type=content_type)


# ── HTTP routes ──────────────────────────────────────────────────────────────

@n8n_proxy_bp.route('/n8n', methods=['GET'])
@login_required
def n8n_root():
    return redirect('/n8n/workflows')


@n8n_proxy_bp.route('/n8n/', defaults={'path': ''})
@n8n_proxy_bp.route('/n8n/<path:path>',
                    methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
@login_required
def proxy(path):
    if path == 'static/base-path.js':
        return Response("window.BASE_PATH = '/n8n/';",
                        content_type='application/javascript')
    return _proxy(path)


@n8n_proxy_bp.route('/healthz', methods=['GET'])
def healthz():
    try:
        r = _req.get(f'{_N8N_ORIGIN}/healthz', timeout=3)
        return Response(r.content, status=r.status_code,
                        content_type=r.headers.get('Content-Type', 'text/plain'))
    except Exception:
        return Response('ok', content_type='text/plain')


@n8n_proxy_bp.route('/assets/<path:path>', methods=['GET'])
def proxy_assets(path):
    return _proxy(f'assets/{path}')


# ── WebSocket proxy for /push ────────────────────────────────────────────────

@_n8n_sock.route('/n8n/rest/push')
def ws_proxy(ws):
    """Proxy WebSocket: browser <-> ANSER <-> n8n Docker."""
    import websocket as ws_client
    import traceback

    print('[WS] === WebSocket proxy started ===', flush=True)

    try:
        token = _get_token()
        print(f'[WS] Token: {"OK" if token else "NONE"}', flush=True)

        try:
            qs = request.query_string.decode('utf-8', errors='replace')
        except Exception:
            qs = ''
        url = f'ws://localhost:5678/rest/push?{qs}'
        print(f'[WS] Connecting to {url}', flush=True)

        cookie = f'n8n-auth={token}' if token else ''
        n8n = ws_client.create_connection(url, cookie=cookie, timeout=10)
        print('[WS] Connected to n8n!', flush=True)
    except Exception as e:
        print(f'[WS] Setup FAILED: {e}', flush=True)
        traceback.print_exc()
        return

    closed = threading.Event()

    def downstream():
        try:
            while not closed.is_set():
                msg = n8n.recv()
                if msg:
                    ws.send(msg)
        except Exception as e:
            print(f'[WS] downstream ended: {e}', flush=True)
        finally:
            closed.set()

    t = threading.Thread(target=downstream, daemon=True)
    t.start()

    try:
        while not closed.is_set():
            msg = ws.receive(timeout=120)
            if msg is None:
                print('[WS] browser disconnected', flush=True)
                break
            n8n.send(msg)
    except Exception as e:
        print(f'[WS] upstream ended: {e}', flush=True)
    finally:
        closed.set()
        try:
            n8n.close()
        except Exception:
            pass
        print('[WS] === WebSocket proxy closed ===', flush=True)
