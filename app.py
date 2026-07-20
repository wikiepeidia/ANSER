import os
import sys
import threading
from datetime import timedelta

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, redirect, request, flash
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from flask_wtf.csrf import CSRFError, generate_csrf
from flask_talisman import Talisman
from authlib.integrations.flask_client import OAuth

# Core Imports
from core.extensions import login_manager, csrf, limiter, db_manager
from flask_login import current_user
from core.models import User
from core.auth import AuthManager
from core.config import Config
from core.automation_engine import AutomationEngine
from core.agent_middleware import AgentMiddleware
from core.services import ai_chat_service, workflow_service
from core.logger import get_logger
from core.security import env_flag, is_local_environment, safe_api_error

sys.stdout.reconfigure(encoding='utf-8')
logger = get_logger(__name__)

# Allow OAuth over HTTP only in local development
if os.environ.get('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Module-level globals kept for backward-compat (populated by create_app)
config = Config()


def _configure_oauth(app):
    """Configure Google OAuth inside the factory (D-04)."""
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
    if not app.config['GOOGLE_CLIENT_ID']:
        print('Warning: GOOGLE_CLIENT_ID not set in environment. OAuth will not work.')

    oauth_client = OAuth(app)
    google = oauth_client.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': (
                'openid email profile '
                'https://www.googleapis.com/auth/drive.readonly '
                'https://www.googleapis.com/auth/drive.file '
                'https://www.googleapis.com/auth/spreadsheets '
                'https://www.googleapis.com/auth/documents '
                'https://www.googleapis.com/auth/gmail.send '
                'https://www.googleapis.com/auth/analytics.readonly'
            )
        },
    )
    # Expose the OAuth client so Blueprint routes can access it via current_app.extensions
    app.extensions['google'] = google


def create_app(config_object=None):
    """Application factory — all initialization happens here (FOUND-01)."""
    cfg = config_object or config

    flask_app = Flask(__name__, template_folder='ui/templates')
    flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # ── Configuration ─────────────────────────────────────────────────────
    _secret = os.environ.get('SECRET_KEY', 'change_me_to_a_secure_random_value')
    if _secret == 'change_me_to_a_secure_random_value' and os.environ.get('FLASK_ENV') != 'development':
        raise RuntimeError("SECRET_KEY must be set to a secure value in production.")
    flask_app.config['SECRET_KEY'] = _secret
    flask_app.config['WTF_CSRF_ENABLED'] = True
    flask_app.secret_key = flask_app.config['SECRET_KEY']
    local_runtime = is_local_environment(cfg)
    if not os.environ.get('FLASK_ENV') and not os.environ.get('APP_ENV') and not getattr(cfg, 'TESTING', False):
        logger.warning(
            "FLASK_ENV/APP_ENV not set — defaulting to production-safe mode "
            "(secure cookies, rate limiting, forced HTTPS). If this is local "
            "development, set FLASK_ENV=development in .env."
        )
    secure_runtime = not local_runtime
    session_cookie_secure = env_flag('SESSION_COOKIE_SECURE', secure_runtime)
    ratelimit_enabled = env_flag('RATELIMIT_ENABLED', secure_runtime)
    force_https = env_flag('FORCE_HTTPS', secure_runtime)
    hsts_enabled = env_flag('STRICT_TRANSPORT_SECURITY', secure_runtime)

    flask_app.config['SESSION_COOKIE_SECURE'] = session_cookie_secure
    flask_app.config['SESSION_COOKIE_HTTPONLY'] = True
    flask_app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # Share the session cookie with the Gateway (:5000) and Sản xuất (:5003)
    # so a single login on Gateway authenticates this app too. Without a
    # Domain attribute, browsers scope cookies to the exact (host, port) that
    # set them, so the Gateway-issued cookie never reaches us on :5002 and
    # the user gets stuck in a redirect loop. Override SESSION_COOKIE_DOMAIN
    # in production (e.g. auto-flowai.com).
    flask_app.config['SESSION_COOKIE_DOMAIN'] = os.environ.get(
        'SESSION_COOKIE_DOMAIN',
        '127.0.0.1' if local_runtime else None,
    )
    flask_app.config['PREFERRED_URL_SCHEME'] = 'https' if force_https else 'http'
    flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    flask_app.config['SESSION_REFRESH_EACH_REQUEST'] = True
    flask_app.config['JSON_AS_ASCII'] = False
    flask_app.config['RATELIMIT_ENABLED'] = ratelimit_enabled
    flask_app.config['RATELIMIT_DEFAULT_LIMITS'] = ['20000 per day', '5000 per hour']
    flask_app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
    flask_app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # disable static file cache in dev

    # ── OAuth ──────────────────────────────────────────────────────────────
    _configure_oauth(flask_app)

    # ── Talisman ───────────────────────────────────────────────────────────
    Talisman(
        flask_app,
        force_https=force_https,
        content_security_policy={
            'default-src': ["'self'"],
            'script-src': [
                "'self'",
                "'unsafe-inline'",
                'https://www.googletagmanager.com',
                'https://www.google-analytics.com',
                'https://cdn.jsdelivr.net',
            ],
            'style-src': [
                "'self'",
                "'unsafe-inline'",
                'https://fonts.googleapis.com',
                'https://cdnjs.cloudflare.com',
                'https://cdn.jsdelivr.net',
            ],
            'img-src': [
                "'self'",
                'data:',
                'https://www.googletagmanager.com',
                'https://www.google-analytics.com',
            ],
            'font-src': [
                "'self'",
                'https://fonts.gstatic.com',
                'https://cdnjs.cloudflare.com',
            ],
            'connect-src': ["'self'", 'https://www.google-analytics.com'],
            'object-src': ["'none'"],
            'frame-ancestors': ["'none'"],
        },
        strict_transport_security=hsts_enabled,
        frame_options='DENY',
        x_content_type_options=True,
        session_cookie_secure=session_cookie_secure,
        force_file_save=False,
    )

    # ── Extensions ────────────────────────────────────────────────────────
    login_manager.init_app(flask_app)
    # No local login_view — signin now lives on the Gateway app (see
    # login_unauthorized() below), not in this codebase.
    csrf.init_app(flask_app)
    limiter.init_app(flask_app)
    flask_app.extensions['database'] = db_manager

    # ── Dependencies stored in extensions (D-05) ──────────────────────────
    auth_manager = AuthManager(db_manager)
    agent_middleware = AgentMiddleware(db_manager)
    automation_engine = AutomationEngine(db_manager)
    flask_app.extensions['auth_manager'] = auth_manager
    flask_app.extensions['agent_middleware'] = agent_middleware
    flask_app.extensions['automation_engine'] = automation_engine
    flask_app.extensions['ai_chat_service'] = ai_chat_service
    flask_app.extensions['workflow_service'] = workflow_service

    # ── Flask-Login callbacks ─────────────────────────────────────────────
    @login_manager.unauthorized_handler
    def login_unauthorized():
        try:
            path = request.path or ''
            accepts_json = 'application/json' in (request.headers.get('Accept') or '')
        except Exception:
            path = ''
            accepts_json = False
        if path.startswith('/api/') or accepts_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Unauthorized - please login'}), 401
        flash('Please log in to continue', 'error')
        # No local signin page anymore — bounce to the Gateway app, with a
        # `next` back here so login lands the user right back where they were.
        next_url = request.url
        return redirect(f"{Config.GATEWAY_ORIGIN}/auth/signin?next={next_url}")

    @login_manager.user_loader
    def load_user(user_id):
        try:
            user_data = auth_manager.get_user_by_id(int(user_id))
            if user_data:
                return User(
                    user_data['id'], user_data['email'],
                    user_data.get('first_name', ''), user_data.get('last_name', ''),
                    user_data.get('role', 'user'),
                    user_data.get('google_token'), user_data.get('avatar'),
                )
        except Exception as e:
            print(f'Error loading user {user_id}: {e}')
        return None

    # ── Context processors ────────────────────────────────────────────────
    @flask_app.context_processor
    def inject_project_config():
        try:
            project_name = getattr(cfg, 'PROJECT_NAME', 'Group Project AI-ML')
        except Exception:
            project_name = 'Group Project AI-ML'
        site_domain = getattr(cfg, 'SITE_DOMAIN', 'localhost:5000')
        base_url = getattr(cfg, 'BASE_URL', f'http://{site_domain}')
        return {'project_name': project_name, 'project_config': cfg,
                'SITE_DOMAIN': site_domain, 'BASE_URL': base_url}

    @flask_app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=lambda: generate_csrf())

    # ── Error handlers ────────────────────────────────────────────────────
    csrf_auth_first_paths = {
        '/api/admin/subscription/auto-renew',
        '/api/admin/subscription/extend',
        '/api/admin/wallet/withdraw',
        '/api/products/import-excel/preview',
        '/api/products/import-excel',
        '/api/workflow/execute',
    }

    @flask_app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.path.startswith('/api/'):
            if request.path in csrf_auth_first_paths and not current_user.is_authenticated:
                return jsonify({'success': False, 'message': 'Unauthorized - please login'}), 401
            return jsonify({'success': False, 'message': 'CSRF token missing or invalid'}), 400
        flash('Security check failed. Please refresh the page and try again.', 'error')
        referer = request.referrer or f"{Config.GATEWAY_ORIGIN}/auth/signin"
        return redirect(referer)

    @flask_app.errorhandler(Exception)
    def handle_api_exception(error):
        if request.path.startswith('/api/'):
            if isinstance(error, HTTPException):
                code = error.code or 500
                if code < 500:
                    return jsonify({'success': False, 'message': error.description}), code
            return safe_api_error(logger, exc=error)
        if isinstance(error, HTTPException):
            return error
        raise error


    # ── Blueprint registration ─────────────────────────────────────────────
    # No auth_bp here — signin/signup/logout live on the Gateway app now.
    from routes.main_routes import main_bp
    from routes.page_routes import page_bp
    from routes.sales_routes import sales_bp
    from routes.workspace_routes import workspace_bp
    from routes.wallet_routes import wallet_bp
    from routes.google_routes import google_bp
    from routes.admin_user_routes import admin_user_bp
    from routes.admin_subscription_routes import admin_sub_bp
    from routes.operations_routes import operations_bp
    from routes.ai_routes import ai_bp
    from routes.inventory_routes import inventory_bp
    from routes.workflow_routes import workflow_bp
    from routes.dl_routes import dl_bp
    from routes.n8n_api import n8n_api_bp
    from routes.admin_warehouse_routes import admin_warehouse_bp

    flask_app.register_blueprint(page_bp)
    flask_app.register_blueprint(main_bp)
    flask_app.register_blueprint(sales_bp)
    flask_app.register_blueprint(workspace_bp)
    flask_app.register_blueprint(wallet_bp)
    flask_app.register_blueprint(google_bp)
    flask_app.register_blueprint(admin_user_bp)
    flask_app.register_blueprint(admin_sub_bp)
    flask_app.register_blueprint(operations_bp)
    flask_app.register_blueprint(inventory_bp)
    flask_app.register_blueprint(workflow_bp)
    flask_app.register_blueprint(ai_bp)
    flask_app.register_blueprint(dl_bp)
    flask_app.register_blueprint(n8n_api_bp)
    flask_app.register_blueprint(admin_warehouse_bp)
    csrf.exempt(n8n_api_bp)

    return flask_app


def run_dl_service():
    current_dir = os.getcwd()
    dl_service_path = os.path.join(current_dir, 'dl_service')
    if dl_service_path not in sys.path:
        sys.path.append(dl_service_path)
    try:
        print('[DL Thread] Importing dl_service.model_app...', flush=True)
        from dl_service.model_app import app as dl_app
        print('[DL Thread] Starting Deep Learning Service on port 5001...', flush=True)
        dl_app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
    except Exception as e:
        print(f'[DL Thread] Error starting DL Service: {e}', flush=True)


def run_n8n():
    """Check n8n reachability. n8n is expected to run externally (Docker or local)."""
    import socket
    import time
    from core.config import Config
    port = int(Config.N8N_PORT)
    for _ in range(10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _s:
            if _s.connect_ex(('localhost', port)) == 0:
                print(f'[n8n] Detected on port {port}.', flush=True)
                return
        time.sleep(2)
    print(f'[n8n] Warning: n8n not reachable on port {port}. '
          'Start Docker container: docker start anser-n8n', flush=True)


if __name__ == '__main__':
    app = create_app()
    if not db_manager.use_postgres:
        db_manager.init_database()
    threading.Thread(target=run_n8n, daemon=True).start()
    port = int(os.environ.get('PORT', 5002))
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False,
            load_dotenv=False, threaded=True)
