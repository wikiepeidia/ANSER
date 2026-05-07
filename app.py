import os
import sys
import json
import uuid
import time
import threading
import requests
import secrets
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFError, generate_csrf
from flask_talisman import Talisman
from authlib.integrations.flask_client import OAuth

# Core Imports
from core.extensions import login_manager, csrf, limiter, db_manager
from core.database import Database
from core.models import User
from core.auth import AuthManager
from core.config import Config
from core.utils import Utils
from core import google_integration
from core.services.analytics_service import analytics_service
from core.automation_engine import AutomationEngine
from core.agent_middleware import AgentMiddleware
sys.stdout.reconfigure(encoding='utf-8')

# Allow OAuth over HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Module-level globals populated by create_app() — routes reference these directly
auth_manager = None
agent_middleware = None
automation_engine = None
google = None
config = Config()
utils = Utils()
db = db_manager  # Alias for convenience

# In-Memory Job Store (For Async AI Tasks)
# Structure: { job_id: { "status": "processing", "result": None, "start_time": timestamp } }
AI_JOBS = {}
JOBS_DIR = os.path.join(os.getcwd(), 'jobs')
os.makedirs(JOBS_DIR, exist_ok=True)

# Central subscription plans (used in wallet/subscription logic)
SUBSCRIPTION_PLANS = {
    'monthly': {'name': 'Monthly', 'days': 30, 'amount': 500000, 'description': 'Monthly plan'},
    'quarterly': {'name': 'Quarterly', 'days': 90, 'amount': 1200000, 'description': 'Quarterly plan'},
    'yearly': {'name': 'Yearly', 'days': 365, 'amount': 4000000, 'description': 'Yearly plan'}
}

def format_plan_dict(plan_key):
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        return None
    return {
        'key': plan_key,
        'name': plan['name'],
        'amount': plan['amount'],
        'days': plan['days'],
        'description': plan.get('description', '')
    }

def parse_db_datetime(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        return None
    if hasattr(value, 'strftime'): # Handle datetime objects
        return value
    if isinstance(value, (str,)):
        # Try multiple formats
        from datetime import datetime
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
    return None

def format_display_datetime(value):
    dt = parse_db_datetime(value)
    return dt.strftime('%d/%m/%Y %H:%M') if dt else None

def parse_metadata(raw_value):
    if not raw_value:
        return {}
    if isinstance(raw_value, dict):
        return raw_value
    try:
        return json.loads(raw_value)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

def _configure_oauth(app):
    """Configure Google OAuth inside the factory (D-04)."""
    global google
    try:
        with open('secrets/google_oauth.json') as f:
            oauth_secrets = json.load(f)
            app.config['GOOGLE_CLIENT_ID'] = oauth_secrets.get('GOOGLE_CLIENT_ID')
            app.config['GOOGLE_CLIENT_SECRET'] = oauth_secrets.get('GOOGLE_CLIENT_SECRET')
    except FileNotFoundError:
        print("Warning: secrets/google_oauth.json not found. OAuth will not work.")
        app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
        app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

    oauth_client = OAuth(app)
    google = oauth_client.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/analytics.readonly'
        }
    )


def create_app(config_object=None):
    """Application factory — all initialization happens here (FOUND-01)."""
    global auth_manager, agent_middleware, automation_engine, db

    cfg = config_object or config

    flask_app = Flask(__name__, template_folder='ui/templates')

    # Apply ProxyFix for correct IP/Scheme behind reverse proxies
    flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # ---- Configuration ----
    flask_app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change_me_to_a_secure_random_value')
    flask_app.config['WTF_CSRF_ENABLED'] = True
    flask_app.secret_key = flask_app.config['SECRET_KEY']
    flask_app.config['SESSION_COOKIE_SECURE'] = False
    flask_app.config['PREFERRED_URL_SCHEME'] = 'http'
    flask_app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    flask_app.config['SESSION_REFRESH_EACH_REQUEST'] = True
    flask_app.config['JSON_AS_ASCII'] = False
    flask_app.config['RATELIMIT_ENABLED'] = False
    flask_app.config['RATELIMIT_DEFAULT_LIMITS'] = ["20000 per day", "5000 per hour"]

    # ---- OAuth config (D-04: inside factory as private helper) ----
    _configure_oauth(flask_app)

    # ---- Talisman (does NOT support init_app — must be called directly) ----
    Talisman(flask_app,
             force_https=False,
             content_security_policy={
                 'default-src': ["'self'", "*"],
                 'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "*"],
                 'style-src': ["'self'", "'unsafe-inline'", "*"],
                 'img-src': ["'self'", "data:", "*"],
                 'font-src': ["'self'", "*"],
                 'object-src': ["'none'"],
                 'frame-ancestors': ["'none'"],
             },
             strict_transport_security=True,
             frame_options='DENY',
             x_content_type_options=True,
             session_cookie_secure=True,
             force_file_save=False)

    # ---- Extension binding (D-01: init_app pattern) ----
    login_manager.init_app(flask_app)
    login_manager.login_view = 'auth.signin'
    csrf.init_app(flask_app)
    limiter.init_app(flask_app)
    flask_app.extensions['database'] = db_manager

    # ---- Non-singleton dependencies (D-05: created here, stored in app.extensions) ----
    auth_manager = AuthManager(db_manager)
    agent_middleware = AgentMiddleware(db_manager)
    automation_engine = AutomationEngine(db_manager)
    db = db_manager
    flask_app.extensions['auth_manager'] = auth_manager
    flask_app.extensions['agent_middleware'] = agent_middleware
    flask_app.extensions['automation_engine'] = automation_engine

    # ---- Unauthorized handler ----
    @login_manager.unauthorized_handler
    def login_unauthorized():
        """Return JSON 401 for api endpoints or redirect to signin for normal routes"""
        try:
            path = request.path or ''
            accepts_json = 'application/json' in (request.headers.get('Accept') or '')
        except Exception:
            path = ''
            accepts_json = False
        if path.startswith('/api/') or accepts_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Unauthorized - please login'}), 401
        flash('Please log in to continue', 'error')
        return redirect(url_for('auth.signin'))

    # ---- User loader (must be AFTER login_manager.init_app) ----
    @login_manager.user_loader
    def load_user(user_id):
        try:
            user_data = auth_manager.get_user_by_id(int(user_id))
            if user_data:
                return User(
                    user_data['id'],
                    user_data['email'],
                    user_data.get('first_name', ''),
                    user_data.get('last_name', ''),
                    user_data.get('role', 'user'),
                    user_data.get('google_token'),
                    user_data.get('avatar')
                )
        except Exception as e:
            print(f"Error loading user {user_id}: {e}")
        return None

    # ---- Context processors ----
    @flask_app.context_processor
    def inject_project_config():
        try:
            project_name = getattr(cfg, 'PROJECT_NAME', 'Group Project AI-ML')
        except Exception:
            project_name = 'Group Project AI-ML'
        site_domain = getattr(cfg, 'SITE_DOMAIN', 'localhost:5000')
        base_url = getattr(cfg, 'BASE_URL', f"http://{site_domain}")
        return {
            'project_name': project_name,
            'project_config': cfg,
            'SITE_DOMAIN': site_domain,
            'BASE_URL': base_url
        }

    @flask_app.context_processor
    def inject_csrf_token():
        """Expose csrf_token helper in all templates."""
        return dict(csrf_token=lambda: generate_csrf())

    # ---- Error handlers ----
    @flask_app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        """Provide graceful feedback when CSRF validation fails."""
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'CSRF token missing or invalid'}), 400
        flash('Security check failed. Please refresh the page and try again.', 'error')
        referer = request.referrer or url_for('auth.signin')
        return redirect(referer)

    # ---- Blueprint registration ----
    flask_app.register_blueprint(auth_bp, url_prefix='/auth')

    # Register domain API blueprints extracted from monolithic app routes.
    from routes.ai_routes import ai_bp
    from routes.inventory_routes import inventory_bp
    from routes.workflow_routes import workflow_bp
    from routes.dl_routes import dl_bp
    from routes.main_routes import register_main_routes

    flask_app.register_blueprint(inventory_bp)
    flask_app.register_blueprint(workflow_bp)
    flask_app.register_blueprint(ai_bp)
    flask_app.register_blueprint(dl_bp)
    register_main_routes(flask_app)

    return flask_app


# ---------------------------------------------------------------------------
# Auth Blueprint (stays at module level until Phase 3)
# ---------------------------------------------------------------------------
from flask import Blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signin', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=['POST'], error_message="Too many login attempts. Please try again later.")
def signin():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']

            user_data = auth_manager.verify_user(email, password)
            if user_data:
                user = User(user_data['id'], user_data['email'], user_data['first_name'],
                            user_data['last_name'],user_data.get('role','user'), user_data.get('google_token'))
                print(">>> Login:", user.email, "role =", user.role)
                login_user(user, remember=True)  # Remember user to extend session
                session.permanent = True  # Set session to use PERMANENT_SESSION_LIFETIME

                # Log activity
                db_manager.log_activity(user.id, 'Login', f'User {user.email} logged in', request.remote_addr)

                flash('Login Successful!', 'success')

                # Redirect based on role
                if user.role == 'admin':
                    return redirect(url_for('admin_workspace'))
                else:
                    return redirect(url_for('workspace'))
            else:
                flash('Invalid email or password!', 'error')
        except Exception as e:
            print(f"Login Error: {e}")
            import traceback
            traceback.print_exc()
            flash('An unexpected error occurred. Please try again later.', 'error')

    return render_template('signin.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit("10 per hour", methods=['POST'], error_message="Too many registrations from this address. Please try again later.")
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone = request.form.get('phone', '')

        print(f"DEBUG: Registering user {email} with role='manager'")
        # Default role is now 'manager' for new signups
        success, message = auth_manager.register_user(email, password, first_name, last_name, phone, role='manager')
        if success:
            # Log activity (we don't have user_id here easily without querying, so maybe skip or query)
            # For simplicity, let's just log it as system activity or try to get the user
            try:
                user_data = auth_manager.get_user_by_email(email)
                if user_data:
                    db_manager.log_activity(user_data['id'], 'Register', f'New user registered: {email}', request.remote_addr)
            except:
                pass

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.signin'))
        else:
            flash(message, 'error')

    return render_template('signup.html')


# ---------------------------------------------------------------------------
# Module-level app instance — replaces old `app = Flask(...)` at line 37
# All @app.route(...) decorators below use this module-level variable.
# ---------------------------------------------------------------------------
app = create_app()

# Main routes moved to routes/main_routes.py


def run_dl_service():
    import sys
    import os
    
    # Add dl_service to system path
    current_dir = os.getcwd()
    dl_service_path = os.path.join(current_dir, 'dl_service')
    if dl_service_path not in sys.path:
        sys.path.append(dl_service_path)
        
    try:
        print("[DL Thread] Importing dl_service.model_app...", flush=True)
        from dl_service.model_app import app as dl_app
        print("[DL Thread] Starting Deep Learning Service on port 5001...", flush=True)
        # Run without reloader to avoid issues in thread
        dl_app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
    except Exception as e:
        print(f"[DL Thread] Error starting DL Service: {e}", flush=True)


if __name__ == '__main__':
    db_manager.init_database()
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)