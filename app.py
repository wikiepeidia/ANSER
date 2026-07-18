"""Gateway — landing page + email/password auth + choose-area.

The single source of truth for the `users` table. Bán lẻ (:5002) and Sản
xuất (:5003) are separate apps that never see a password — they just
trust the session cookie this app issues (same SECRET_KEY, host-scoped
cookie, not port-scoped) and read `users` read-only to resolve who's
logged in.

Google OAuth login stays on Retail (:5002) for now — not extracted here.
"""
import os
from datetime import timedelta

from core.env_loader import load_project_env
load_project_env()

from flask import Flask, jsonify, redirect, request, flash, url_for  # noqa: E402
from flask_wtf.csrf import CSRFError, generate_csrf  # noqa: E402
from werkzeug.exceptions import HTTPException  # noqa: E402

from core.config import Config  # noqa: E402
from core.extensions import login_manager, csrf, limiter, db_manager  # noqa: E402
from core.models import User  # noqa: E402
from core.auth import AuthManager  # noqa: E402
from core.logger import get_logger  # noqa: E402

logger = get_logger(__name__)


def create_app():
    app = Flask(__name__, template_folder='ui/templates')

    secret = os.environ.get('SECRET_KEY', Config.SECRET_KEY)
    app.config['SECRET_KEY'] = secret
    app.secret_key = secret
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True
    app.config['RATELIMIT_DEFAULT_LIMITS'] = ['20000 per day', '5000 per hour']

    login_manager.init_app(app)
    login_manager.login_view = 'auth.signin'
    csrf.init_app(app)
    limiter.init_app(app)
    app.extensions['database'] = db_manager
    app.extensions['auth_manager'] = AuthManager(db_manager)

    @login_manager.unauthorized_handler
    def login_unauthorized():
        if request.path.startswith('/api/') or 'application/json' in (request.headers.get('Accept') or ''):
            return jsonify({'success': False, 'message': 'Unauthorized - please login'}), 401
        flash('Vui lòng đăng nhập để tiếp tục', 'error')
        return redirect(url_for('auth.signin'))

    @login_manager.user_loader
    def load_user(user_id):
        try:
            auth_manager = app.extensions['auth_manager']
            data = auth_manager.get_user_by_id(int(user_id))
            if data:
                return User(
                    data['id'], data['email'], data.get('first_name', ''),
                    data.get('last_name', ''), data.get('role', 'user'),
                    data.get('google_token'), data.get('avatar'),
                )
        except Exception as e:
            logger.error('Error loading user %s: %s', user_id, e)
        return None

    @app.context_processor
    def inject_project_config():
        return {'project_name': Config.PROJECT_NAME, 'project_config': Config,
                'SITE_DOMAIN': Config.SITE_DOMAIN, 'BASE_URL': Config.BASE_URL,
                'retail_origin': Config.RETAIL_ORIGIN, 'sanxuat_origin': Config.SANXUAT_ORIGIN}

    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=lambda: generate_csrf())

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'message': 'CSRF token missing or invalid'}), 400
        flash('Security check failed. Please refresh the page and try again.', 'error')
        return redirect(request.referrer or url_for('auth.signin'))

    @app.errorhandler(Exception)
    def handle_exception(error):
        if request.path.startswith('/api/'):
            if isinstance(error, HTTPException):
                code = error.code or 500
                if code < 500:
                    return jsonify({'success': False, 'message': error.description}), code
            logger.error('Unhandled error: %s', error, exc_info=True)
            return jsonify({'success': False, 'message': 'Internal server error'}), 500
        if isinstance(error, HTTPException):
            return error
        raise error

    from routes.auth_routes import auth_bp
    from routes.page_routes import page_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(page_bp)

    return app


app = create_app()

if __name__ == '__main__':
    if not db_manager.use_postgres:
        db_manager.init_database()
    app.run(host='127.0.0.1', port=Config.PORT, debug=True, use_reloader=True)
