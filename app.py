"""San Xuat — separate Flask app, separate API/DB from ANSER, port 5001.

Auth is NOT handled here — users sign in on the ANSER app (port 5000).
This app only reads the shared `users` table (core/auth_db.py) to resolve
the session cookie Flask-Login already validated (same SECRET_KEY as
ANSER, so the cookie set on :5000 is recognized here too — cookies are
scoped by host, not port). If there's no valid session, we bounce back to
ANSER's signin page.
"""
import os

from core.env_loader import load_project_env

load_project_env()

from flask import Flask, redirect  # noqa: E402
from flask_login import LoginManager  # noqa: E402

from core.config import Config  # noqa: E402
from core.extensions import login_manager, csrf  # noqa: E402
from core.models import User  # noqa: E402
from core.sanxuat_db import init_db  # noqa: E402


def create_app():
    app = Flask(__name__)

    secret = os.environ.get('SECRET_KEY', Config.SECRET_KEY)
    app.config['SECRET_KEY'] = secret
    app.secret_key = secret
    # Same cookie policy as ANSER so the session cookie set on :5000 is
    # accepted here too (host-scoped, not port-scoped).
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_HTTPONLY'] = True

    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from core.auth_db import get_user_by_id
        try:
            data = get_user_by_id(int(user_id))
        except Exception:
            return None
        if not data:
            return None
        return User(
            data['id'], data['email'], data.get('first_name', ''),
            data.get('last_name', ''), data.get('role', 'user'), data.get('avatar'),
        )

    @login_manager.unauthorized_handler
    def unauthorized():
        # No local signin page — bounce back to Gateway's, then return here.
        next_url = f"http://127.0.0.1:{Config.PORT}/"
        return redirect(f"{Config.GATEWAY_ORIGIN}/auth/signin?next={next_url}")

    from routes.page_routes import page_bp
    from routes.api_routes import api_bp
    from routes.n8n_api import n8n_api_bp
    from routes.production_routes import production_bp
    from routes.inventory_routes import inventory_bp
    from routes.warehouse_routes import warehouse_bp
    from routes.internal_admin_routes import internal_admin_bp
    from routes.supplier_routes import supplier_bp
    from routes.costing_routes import costing_bp
    from routes.invoice_routes import invoice_bp
    app.register_blueprint(page_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(n8n_api_bp)
    app.register_blueprint(production_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(internal_admin_bp)
    app.register_blueprint(supplier_bp)
    app.register_blueprint(costing_bp)
    app.register_blueprint(invoice_bp)

    init_db()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=Config.PORT, debug=True, use_reloader=True)
