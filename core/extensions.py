# core/extensions.py
"""
Shared Flask extension singletons.

All objects are created WITHOUT a Flask app instance so they can be
imported by Blueprint files without triggering circular imports.

Each extension is bound to a specific app instance inside create_app()
using the init_app() pattern:

    from core.extensions import login_manager, csrf, limiter, db_manager
    def create_app():
        ...
        login_manager.init_app(app)
        csrf.init_app(app)
        limiter.init_app(app)
        app.extensions['database'] = db_manager
"""
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.database import Database

# LoginManager — login_view and user_loader registered inside create_app()
login_manager = LoginManager()

# CSRFProtect — bound to app via csrf.init_app(app) inside create_app()
csrf = CSRFProtect()

# Limiter — NO app= arg, NO default_limits here.
# Set app.config['RATELIMIT_DEFAULT_LIMITS'] before limiter.init_app(app) in create_app()
limiter = Limiter(get_remote_address)

# Database — connects to SQLite directly; no Flask app dependency
db_manager = Database()
