import hashlib
from functools import wraps
from flask import session, redirect, url_for, flash

class AuthManager:
    def __init__(self, database):
        self.db = database
    
    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_user(self, email, password):
        conn = self.db.get_connection()
        c = conn.cursor()
        hashed_pw = AuthManager.hash_password(password)
        c.execute('SELECT id, email, name, avatar, role FROM users WHERE email = ? AND password = ?', 
                 (email, hashed_pw))
        user = c.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0],
                'email': user[1], 
                'first_name': user[2].split()[0] if user[2] else '',
                'last_name': user[2].split()[1] if len(user[2].split()) > 1 else '',
                'role': user[4]
            }
        return None
    
    def register_user(self, email, password, first_name, last_name, phone=''):
        conn = self.db.get_connection()
        c = conn.cursor()
        try:
            hashed_pw = AuthManager.hash_password(password)
            full_name = f"{first_name} {last_name}"
            c.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', 
                     (full_name, email, hashed_pw))
            user_id = c.lastrowid
            
            # Create default personal workspace
            c.execute('''INSERT INTO workspaces (user_id, name, type, description) 
                        VALUES (?, ?, ?, ?)''',
                     (user_id, f"{first_name}'s Personal Workspace", 'personal', 
                      'Your personal productivity space'))
            
            conn.commit()
            return True, "Đăng ký thành công!"
        except Exception as e:
            print(f"Error creating user: {e}")
            return False, "Email đã được sử dụng!"
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id):
        conn = self.db.get_connection()
        c = conn.cursor()
        c.execute('SELECT id, email, name, avatar, role FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0],
                'email': user[1], 
                'first_name': user[2].split()[0] if user[2] else '',
                'last_name': user[2].split()[1] if len(user[2].split()) > 1 else '',
                'role': user[4]
            }
        return None
    
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
                flash('Vui lòng đăng nhập để tiếp tục', 'error')
                return redirect(url_for('auth.signin'))
            return f(*args, **kwargs)
        return decorated_function