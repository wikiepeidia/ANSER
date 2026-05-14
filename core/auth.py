import hashlib
from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from core.google_integration import send_email

class AuthManager:
    def __init__(self, database):
        self.db = database
    
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_user(self, email, password):
        conn = self.db.get_connection()
        try:
            c = conn.cursor()
            hashed_pw = AuthManager.hash_password(password)
            # Check if google_token column exists (it should, but for safety in query)
            # We assume schema is updated.
            c.execute('SELECT id, email, name, avatar, role, google_token FROM users WHERE email = ? AND password = ?', 
                     (email, hashed_pw))
            user = c.fetchone()
            
            if user:
                return {
                    'id': user[0],
                    'email': user[1], 
                    'first_name': user[2].split()[0] if user[2] else '',
                    'last_name': ' '.join(user[2].split()[1:]) if user[2] and len(user[2].split()) > 1 else '',
                    'avatar': user[3],
                    'role': user[4],
                    'google_token': user[5]
                }
            return None
        except Exception as e:
            print(f"Error verifying user: {e}")
            return None
        finally:
            conn.close()
    
    def register_user(self, email, password, first_name, last_name, phone='', role='manager', manager_id=None):
        conn = self.db.get_connection()
        c = conn.cursor()
        try:
            hashed_pw = AuthManager.hash_password(password)
            full_name = f"{first_name} {last_name}"
            
            # Check columns
            columns = self.db.get_table_columns('users', cursor=c)
            
            if 'manager_id' in columns:
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
            
            # Send Welcome Email
            try:
                subject = "Chào mừng bạn đến với Workflow Automation!"
                body = f"""Xin chào {first_name},

Chào mừng bạn đến với Workflow Automation for Retail! Chúng tôi rất vui khi có bạn tham gia.

Tài khoản của bạn đã được tạo thành công. Bạn có thể bắt đầu xây dựng các quy trình tự động hóa thông minh cho doanh nghiệp bán lẻ của mình.

Bắt đầu khám phá không gian làm việc cá nhân của bạn:
- Quản lý khách hàng
- Theo dõi hàng tồn kho
- Tự động hóa tác vụ

Nếu bạn có bất kỳ câu hỏi nào, vui lòng liên hệ với chúng tôi.

Trân trọng,
Đội ngũ Workflow Automation
"""
                send_email(email, subject, body)
            except Exception as e:
                print(f"Failed to send welcome email: {e}")

            return True, "Đăng ký thành công!"
        except Exception as e:
            print(f"Error creating user: {e}")
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
                    'id': user[0],
                    'email': user[1], 
                    'first_name': user[2].split()[0] if user[2] else '',
                    'last_name': ' '.join(user[2].split()[1:]) if user[2] and len(user[2].split()) > 1 else '',
                    'avatar': user[3],
                    'role': user[4],
                    'google_token': user[5]
                }
            return None
        except Exception as e:
            print(f"Error getting user by id: {e}")
            return None
        finally:
            conn.close()
    
    def get_user_workspaces(self, user_id):
        conn = self.db.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM workspaces WHERE user_id = ? ORDER BY created_at', (user_id,))
        workspaces = c.fetchall()
        conn.close()
        return workspaces
    
    @staticmethod
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                # If this is an API call, return a JSON 401 instead of HTML redirect
                try:
                    path = request.path or ''
                    is_api = path.startswith('/api/')
                    is_accepting_json = 'application/json' in (request.headers.get('Accept') or '')
                except Exception:
                    is_api = False
                    is_accepting_json = False

                if is_api or is_accepting_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Chưa đăng nhập'}), 401
                # fallback to redirect for normal page loads
                flash('Vui lòng đăng nhập để tiếp tục', 'error')
                return redirect(url_for('auth.signin'))
            return f(*args, **kwargs)
        return decorated_function
    
    @staticmethod
    def permission_required(permission_type):
        """Decorator to check if user has specific permission"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                from flask import jsonify, current_app
                from flask_login import current_user
                
                if not current_user.is_authenticated:
                    return jsonify({'success': False, 'message': 'Chưa đăng nhập'}), 401
                
                # Admin and Manager have all permissions
                if hasattr(current_user, 'role') and current_user.role in ['admin', 'manager']:
                    return f(*args, **kwargs)
                
                # Kiểm tra permission trong database
                db = current_app.extensions.get('database')
                if db and db.has_permission(current_user.id, permission_type):
                    return f(*args, **kwargs)
                
                return jsonify({'success': False, 'message': f'Permission denied: {permission_type} required'}), 403
            
            return decorated_function
        return decorator