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
        conn = self.db.get_connection()
        try:
            c = conn.cursor()
            
            # Try to fetch with password_version, fall back if column is missing
            try:
                c.execute('SELECT id, email, name, avatar, role, google_token, password, password_version FROM users WHERE email = ?', (email,))
                user = c.fetchone()
                password_version_available = True
            except Exception as schema_err:
                logger.warning("password_version column not found (schema error: %s) — falling back to legacy mode", schema_err)
                c.execute('SELECT id, email, name, avatar, role, google_token, password FROM users WHERE email = ?', (email,))
                user = c.fetchone()
                password_version_available = False

            if not user:
                return None

            stored_pw = user['password']

            # ─────────────────────────────────────────────────────────────
            # THE FIX: Look at the actual hash string to determine the algorithm!
            # Bcrypt hashes always start with $2b$ or $2a$
            # ─────────────────────────────────────────────────────────────
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
                
                # Upgrade to bcrypt if possible
                if password_version_available:
                    new_hash = AuthManager.hash_password(password)
                    try:
                        c.execute('UPDATE users SET password = ?, password_version = 1 WHERE id = ?', (new_hash, user['id']))
                        conn.commit()
                    except Exception as update_err:
                        logger.warning("Failed to update password_version: %s", update_err)
                        conn.rollback()

            return {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['name'].split()[0] if user['name'] else '',
                'last_name': ' '.join(user['name'].split()[1:]) if user['name'] and len(user['name'].split()) > 1 else '',
                'avatar': user['avatar'],
                'role': user['role'],
                'google_token': user['google_token'],
            }
        except Exception as e:
            logger.error("Error verifying user: %s", e, exc_info=True)
            return None
        finally:
            conn.close()
    
    def register_user(self, email, password, first_name, last_name, phone='', role='manager', manager_id=None):
        conn = self.db.get_connection()
        c = conn.cursor()
        try:
            hashed_pw = AuthManager.hash_password(password)
            full_name = f"{first_name} {last_name}"

            columns = self.db.get_table_columns('users', cursor=c)
            has_password_version = 'password_version' in columns
            has_manager_id = 'manager_id' in columns

            if has_password_version and has_manager_id:
                c.execute('INSERT INTO users (name, email, password, password_version, role, manager_id) VALUES (?, ?, ?, 1, ?, ?)',
                         (full_name, email, hashed_pw, role, manager_id))
            elif has_password_version:
                c.execute('INSERT INTO users (name, email, password, password_version, role) VALUES (?, ?, ?, 1, ?)',
                         (full_name, email, hashed_pw, role))
            elif has_manager_id:
                c.execute('INSERT INTO users (name, email, password, role, manager_id) VALUES (?, ?, ?, ?, ?)',
                         (full_name, email, hashed_pw, role, manager_id))
            else:
                c.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
                         (full_name, email, hashed_pw, role))
                
            user_id = c.lastrowid
            
            # Create default personal workspace
            c.execute('''INSERT INTO workspaces (user_id, name, type, description) 
                        VALUES (?, ?, ?, ?)''',
                     (user_id, f"{first_name}'s Personal Workspace", 'personal', 
                      'Your personal productivity space'))
            
            conn.commit()
            
            # Send Welcome Email (Fail silently if it doesn't work locally)
            try:
                subject = "Chào mừng bạn đến với Workflow Automation!"
                body = f"""Xin chào {first_name},\n\nChào mừng bạn đến với Workflow Automation for Retail! Chúng tôi rất vui khi có bạn tham gia.\n\nTài khoản của bạn đã được tạo thành công."""
                send_email(email, subject, body)
            except Exception as e:
                logger.warning("Failed to send welcome email to %s: %s", email, e)

            return True, "Đăng ký thành công!"
        except Exception as e:
            logger.error("Error creating user %s: %s", email, e, exc_info=True)
            return False, "Email đã được sử dụng!"
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id):
        conn = self.db.get_connection()
        try:
            c = conn.cursor()
            c.execute('SELECT id, email, name, avatar, role, google_token FROM users WHERE id = ?', (user_id,))
            user = c.fetchone()
            
            if user:
                return {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['name'].split()[0] if user['name'] else '',
                    'last_name': ' '.join(user['name'].split()[1:]) if user['name'] and len(user['name'].split()) > 1 else '',
                    'avatar': user['avatar'],
                    'role': user['role'],
                    'google_token': user['google_token'],
                }
            return None
        except Exception as e:
            logger.error("Error getting user by id %s: %s", user_id, e, exc_info=True)
            return None
        finally:
            conn.close()
    
    def get_user_workspaces(self, user_id):
        conn = self.db.get_connection()
        c = conn.cursor()
        c.execute(
            'SELECT id, user_id, name, type, description, is_active, created_at'
            ' FROM workspaces WHERE user_id = ? ORDER BY created_at',
            (user_id,),
        )
        workspaces = c.fetchall()
        conn.close()
        return workspaces
    
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