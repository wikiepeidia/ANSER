from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from core.google_integration import send_email
import bcrypt
from core.logger import get_logger

logger = get_logger(__name__)

class AuthManager:
    def __init__(self, database):
        self.db = database

    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(password, hashed):
        try:
            return bcrypt.checkpw(password.encode(), hashed.encode() if isinstance(hashed, str) else hashed)
        except Exception:
            return False

    def verify_user(self, email, password):
        try:
            user = self.db.get_user_by_email(email)
            if not user:
                return None

            stored_pw = user.get('password')
            password_version = user.get('password_version', 0)

            # Look at the actual hash string to determine the algorithm
            # Bcrypt hashes always start with $2b$ or $2a$
            if stored_pw and stored_pw.startswith('$2'):
                # Modern bcrypt hash
                if not AuthManager.verify_password(password, stored_pw):
                    return None
            else:
                # Legacy sha256 hash
                import hashlib
                legacy_hash = hashlib.sha256(password.encode()).hexdigest()
                if legacy_hash != stored_pw:
                    return None
                # Rehash with bcrypt for next login
                new_hash = AuthManager.hash_password(password)
                self.db.update_password(user['id'], new_hash, version=1)

            # Return standardized user dictionary (without password)
            return {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'avatar': user['avatar'],
                'role': user['role'],
                'google_token': user['google_token'],
            }
        except Exception as e:
            logger.error("Error verifying user: %s", e, exc_info=True)
            return None
    
    def register_user(self, email, password, first_name, last_name, phone='', role='manager', manager_id=None):
        try:
            user_id = self.db.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                manager_id=manager_id
            )
            
            # Send Welcome Email (Fail silently if it doesn't work locally)
            try:
                subject = "Chào mừng bạn đến với Workflow Automation!"
                body = f"""Xin chào {first_name},\n\nChào mừng bạn đến với Workflow Automation for Retail! Chúng tôi rất vui khi có bạn tham gia.\n\nTài khoản của bạn đã được tạo thành công."""
                send_email(email, subject, body)
            except Exception as e:
                logger.warning("Failed to send welcome email to %s: %s", email, e)

            return True, "Đăng ký thành công!"
        except Exception as e:
            if 'Email exists' in str(e):
                return False, "Email đã được sử dụng!"
            logger.error("Error creating user %s: %s", email, e, exc_info=True)
            return False, f"Lỗi đăng ký: {str(e)}"
    
    def get_user_by_id(self, user_id):
        try:
            return self.db.get_user_by_id(user_id)
        except Exception as e:
            logger.error("Error getting user by id %s: %s", user_id, e, exc_info=True)
            return None

    def get_user_by_email(self, email):
        try:
            return self.db.get_user_by_email(email)
        except Exception as e:
            logger.error("Error getting user by email %s: %s", email, e, exc_info=True)
            return None
    
    def get_user_workspaces(self, user_id):
        try:
            return self.db.get_user_workspaces(user_id)
        except Exception as e:
            logger.error("Error getting user workspaces for %s: %s", user_id, e, exc_info=True)
            return []
    
    @staticmethod
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                try:
                    path = request.path or ''
                    is_api = path.startswith('/api/')
                    is_accepting_json = 'application/json' in (request.headers.get('Accept') or '')
                except Exception:
                    is_api = False
                    is_accepting_json = False

                if is_api or is_accepting_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Chưa đăng nhập'}), 401
                
                flash('Vui lòng đăng nhập để tiếp tục', 'error')
                return redirect(url_for('auth.signin'))
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def permission_required(permission_type):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                from flask import jsonify, current_app
                from flask_login import current_user
                
                if not current_user.is_authenticated:
                    return jsonify({'success': False, 'message': 'Chưa đăng nhập'}), 401
                
                if hasattr(current_user, 'role') and current_user.role in ['admin', 'manager']:
                    return f(*args, **kwargs)
                
                db = current_app.extensions.get('database')
                if db and db.has_permission(current_user.id, permission_type):
                    return f(*args, **kwargs)
                
                return jsonify({'success': False, 'message': f'Permission denied: {permission_type} required'}), 403
            
            return decorated_function
        return decorator