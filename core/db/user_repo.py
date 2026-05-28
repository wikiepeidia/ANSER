"""User repository — users and workspaces tables."""
import bcrypt
from core.logger import get_logger

logger = get_logger(__name__)


def _is_postgres(conn) -> bool:
    return hasattr(conn, '_pool')


class UserRepo:
    def __init__(self, conn):
        self.conn = conn

    def get_user_by_id(self, user_id):
        c = self.conn.cursor()
        try:
            c.execute(
                'SELECT id, email, name, avatar, theme, role,'
                ' first_name, last_name, google_token FROM users WHERE id = ?',
                (user_id,),
            )
            user = c.fetchone()
            if user:
                return {
                    'id': user['id'], 'email': user['email'], 'name': user['name'],
                    'avatar': user['avatar'], 'theme': user['theme'], 'role': user['role'],
                    'first_name': user['first_name'], 'last_name': user['last_name'],
                    'google_token': user['google_token'],
                }
        except Exception:
            try:
                c.execute(
                    'SELECT id, email, name, avatar, theme, role FROM users WHERE id = ?',
                    (user_id,),
                )
                user = c.fetchone()
                if user:
                    return {
                        'id': user['id'], 'email': user['email'], 'name': user['name'],
                        'avatar': user['avatar'], 'theme': user['theme'], 'role': user['role'],
                        'first_name': None, 'last_name': None, 'google_token': None,
                    }
            except Exception:
                pass
        return None

    def create_user(self, email, password, name, role='user',
                    first_name=None, last_name=None, manager_id=None):
        c = self.conn.cursor()
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            has_first_name = self._has_column(c, 'users', 'first_name')
            if has_first_name:
                c.execute(
                    'INSERT INTO users'
                    ' (email, password, password_version, name, role, first_name, last_name, manager_id)'
                    ' VALUES (?, ?, 1, ?, ?, ?, ?, ?)',
                    (email, hashed_pw, name, role, first_name, last_name, manager_id),
                )
            else:
                c.execute(
                    'INSERT INTO users'
                    ' (email, password, password_version, name, role, manager_id)'
                    ' VALUES (?, ?, 1, ?, ?, ?)',
                    (email, hashed_pw, name, role, manager_id),
                )
            user_id = c.lastrowid
            self.conn.commit()
            return user_id
        except Exception as e:
            if "UNIQUE constraint" in str(e) or "duplicate key" in str(e):
                raise Exception('Email exists')
            raise

    def get_user_workspaces(self, user_id):
        c = self.conn.cursor()
        c.execute(
            'SELECT id, user_id, name, type, description, is_active, created_at'
            ' FROM workspaces WHERE user_id = ? ORDER BY created_at',
            (user_id,),
        )
        return c.fetchall()

    def get_all_users_with_permissions(self):
        c = self.conn.cursor()
        c.execute("SELECT u.id, u.name, u.email, u.role, '' as permissions FROM users u")
        return [
            {'id': row['id'], 'name': row['name'], 'email': row['email'],
             'role': row['role'], 'permissions': []}
            for row in c.fetchall()
        ]

    # ── helpers ──────────────────────────────────────────────────────────────

    def _has_column(self, cursor, table, column) -> bool:
        try:
            if _is_postgres(self.conn):
                cursor.execute(
                    "SELECT 1 FROM information_schema.columns"
                    " WHERE table_name = ? AND column_name = ?",
                    (table, column),
                )
            else:
                cursor.execute(f"PRAGMA table_info({table})")
                return any(row['name'] == column for row in cursor.fetchall())
            return cursor.fetchone() is not None
        except Exception:
            return False
