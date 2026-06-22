"""Authentication Blueprint — signin and signup extracted from app.py."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask import current_app
from flask_login import login_user, logout_user

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
                
                # Sync Flask-Login with custom AuthManager session check
                login_user(user, remember=True)
                session['user_id'] = user.id  
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
                conn = db_manager.get_connection()
                c = conn.cursor()
                c.execute('SELECT id FROM users WHERE email = ?', (email,))
                user_row = c.fetchone()
                conn.close()
                
                if user_row:
                    db_manager.log_activity(user_row['id'], 'Register', f'New user registered: {email}', request.remote_addr)
            except Exception as e:
                logger.error("Error logging registration: %s", e)
                
            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('auth.signin'))
            
        flash(message, 'error')
    return render_template('signup.html')

@auth_bp.route('/logout')
def logout():
    """Proper logout route to clear the session cleanly."""
    if 'user_id' in session:
        db_manager.log_activity(session['user_id'], 'Logout', 'User logged out', request.remote_addr)
    session.pop('user_id', None)
    logout_user()
    flash('Bạn đã đăng xuất thành công.', 'success')
    return redirect(url_for('auth.signin'))