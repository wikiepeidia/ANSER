"""Authentication Blueprint — signin, signup, logout. The only place in the
whole system that verifies a password or creates a user."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from flask_login import login_user, logout_user

from core.config import Config
from core.extensions import db_manager, limiter
from core.models import User
from core.logger import get_logger

logger = get_logger(__name__)

auth_bp = Blueprint('auth', __name__)

_TRUSTED_ORIGINS = (Config.RETAIL_ORIGIN, Config.SANXUAT_ORIGIN)


def _skip_limiter_in_tests():
    return current_app.config.get('TESTING', False)


def _safe_next_url():
    next_url = request.form.get('next') or request.args.get('next')
    if next_url and any(next_url.startswith(origin) for origin in _TRUSTED_ORIGINS):
        return next_url
    return None


@auth_bp.route('/signin', methods=['GET', 'POST'])
@limiter.limit(
    "5 per minute",
    methods=['POST'],
    error_message="Quá nhiều lần thử đăng nhập. Vui lòng thử lại sau.",
    exempt_when=_skip_limiter_in_tests,
)
def signin():
    auth_manager = current_app.extensions['auth_manager']
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            user_data = auth_manager.verify_user(email, password)
            if user_data:
                user = User(
                    user_data['id'], user_data['email'],
                    user_data['first_name'], user_data['last_name'],
                    user_data.get('role', 'user'), user_data.get('google_token')
                )
                logger.info("Login: %s role=%s", user.email, user.role)

                login_user(user, remember=True)
                session['user_id'] = user.id
                session.permanent = True

                db_manager.log_activity(user.id, 'Login', f'User {user.email} logged in', request.remote_addr)
                flash('Đăng nhập thành công!', 'success')

                next_url = _safe_next_url()
                if next_url:
                    return redirect(next_url)
                if user.role == 'admin':
                    return redirect(f"{Config.RETAIL_ORIGIN}/admin")
                return redirect(url_for('pages.choose_area'))

            flash('Email hoặc mật khẩu không đúng!', 'error')
        except Exception as e:
            logger.error("Login error: %s", e, exc_info=True)
            flash('Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau.', 'error')
    return render_template('signin.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit(
    "10 per hour",
    methods=['POST'],
    error_message="Quá nhiều lần đăng ký từ địa chỉ này. Vui lòng thử lại sau.",
    exempt_when=_skip_limiter_in_tests,
)
def signup():
    auth_manager = current_app.extensions['auth_manager']
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            first_name = request.form.get('first_name', '')
            last_name = request.form.get('last_name', '')
            ok, message = auth_manager.register_user(email, password, first_name, last_name)
            if ok:
                flash(message, 'success')
                return redirect(url_for('auth.signin'))
            flash(message, 'error')
        except Exception as e:
            logger.error("Signup error: %s", e, exc_info=True)
            flash('Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau.', 'error')
    return render_template('signup.html')


@auth_bp.route('/logout')
def logout():
    """Clears the shared session cookie — logs the user out of every mảng."""
    if 'user_id' in session:
        try:
            db_manager.log_activity(session['user_id'], 'Logout', 'User logged out', request.remote_addr)
        except Exception:
            pass
    session.pop('user_id', None)
    session.pop('active_area', None)
    logout_user()
    flash('Bạn đã đăng xuất thành công.', 'success')
    return redirect(url_for('pages.landing'))
