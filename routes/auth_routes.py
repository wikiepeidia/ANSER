"""Authentication Blueprint — signin and signup extracted from app.py."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask import current_app
from flask_login import login_user

from core.extensions import db_manager, limiter
from core.models import User
from core.logger import get_logger

logger = get_logger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/signin', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=['POST'], error_message="Quá nhiều lần thử đăng nhập. Vui lòng thử lại sau.")
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
                session.permanent = True
                db_manager.log_activity(user.id, 'Login', f'User {user.email} logged in', request.remote_addr)
                flash('Đăng nhập thành công!', 'success')
                if user.role == 'admin':
                    return redirect(url_for('pages.admin_dashboard'))
                return redirect(url_for('pages.dashboard'))
            flash('Email hoặc mật khẩu không đúng!', 'error')
        except Exception as e:
            logger.error("Login error: %s", e, exc_info=True)
            flash('Đã xảy ra lỗi không mong muốn. Vui lòng thử lại sau.', 'error')
    return render_template('signin.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit("10 per hour", methods=['POST'], error_message="Quá nhiều lần đăng ký từ địa chỉ này. Vui lòng thử lại sau.")
def signup():
    auth_manager = current_app.extensions['auth_manager']
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone = request.form.get('phone', '')
        logger.info("Registering user %s with role='manager'", email)
        success, message = auth_manager.register_user(email, password, first_name, last_name, phone, role='manager')
        if success:
            try:
                user_data = auth_manager.get_user_by_email(email)
                if user_data:
                    db_manager.log_activity(user_data['id'], 'Register', f'New user registered: {email}', request.remote_addr)
            except Exception:
                pass
            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('auth.signin'))
        flash(message, 'error')
    return render_template('signup.html')
