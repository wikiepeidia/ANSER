"""User repository — users and workspaces tables."""
import bcrypt
from core.logger import get_logger

logger = get_logger(__name__)


def _is_postgres(conn) -> bool:
    return hasattr(conn, '_pool')


class UserRepo:
    def __init__(self, conn, business_conn=None):
        """`conn` is the auth-DB connection (users table). `business_conn`
        is the separate business-DB connection, used only for the "create
        a default personal workspace" side effect on signup — defaults to
        `conn` itself so single-connection callers (SQLite dev/tests, where
        both tables live in the same file) keep working unchanged."""
        self.conn = conn
        self.business_conn = business_conn if business_conn is not None else conn

    def get_user_by_id(self, user_id):
        c = self.conn.cursor()
        try:
            # Try to fetch all columns including the new ones
            c.execute(
                'SELECT id, email, name, avatar, role, first_name, last_name, google_token FROM users WHERE id = ?',
                (user_id,),
            )
            user = c.fetchone()
            if user:
                return self._standardize_user(user)
        except Exception as e:
            # Fallback for legacy schema
            logger.debug("get_user_by_id fallback triggered: %s", e)
            try:
                c.execute(
                    'SELECT id, email, name, role FROM users WHERE id = ?',
                    (user_id,),
                )
                user = c.fetchone()
                if user:
                    return self._standardize_user(user)
            except Exception:
                pass
        return None

    def get_user_by_email(self, email):
        c = self.conn.cursor()
        try:
            # We also need password and password_version for AuthManager.verify_user
            c.execute(
                'SELECT id, email, name, avatar, role, first_name, last_name, google_token, password, password_version FROM users WHERE email = ?',
                (email,),
            )
            user = c.fetchone()
            if user:
                return self._standardize_user(user, include_password=True)
        except Exception as e:
            logger.debug("get_user_by_email fallback triggered: %s", e)
            try:
                c.execute(
                    'SELECT id, email, name, role, password FROM users WHERE email = ?',
                    (email,),
                )
                user = c.fetchone()
                if user:
                    return self._standardize_user(user, include_password=True)
            except Exception:
                pass
        return None

    def create_user(self, email, password, first_name, last_name, role='user', manager_id=None):
        c = self.conn.cursor()
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        full_name = f"{first_name} {last_name}".strip()
        try:
            has_first_name = self._has_column(c, 'users', 'first_name')
            has_password_version = self._has_column(c, 'users', 'password_version')
            has_manager_id = self._has_column(c, 'users', 'manager_id')

            cols = ['email', 'password', 'name', 'role']
            vals = [email, hashed_pw, full_name, role]
            placeholders = ['?', '?', '?', '?']

            if has_first_name:
                cols.extend(['first_name', 'last_name'])
                vals.extend([first_name, last_name])
                placeholders.extend(['?', '?'])
            
            if has_password_version:
                cols.append('password_version')
                vals.append(1)
                placeholders.append('?')

            if has_manager_id:
                cols.append('manager_id')
                vals.append(manager_id)
                placeholders.append('?')

            query = f"INSERT INTO users ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
            c.execute(query, tuple(vals))
            user_id = c.lastrowid
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            if "UNIQUE constraint" in str(e) or "duplicate key" in str(e):
                raise Exception('Email exists')
            raise

        # Default personal workspace lives in the business DB — a separate
        # connection now. Created after the user row commits: if this step
        # fails the user can still sign in and get a workspace later, which
        # is safer than a workspace existing with no matching user.
        try:
            bc = self.business_conn.cursor()
            bc.execute(
                'INSERT INTO workspaces (user_id, name, type, description) VALUES (?, ?, ?, ?)',
                (user_id, f"{first_name}'s Personal Workspace", 'personal', 'Your personal productivity space')
            )
            self.business_conn.commit()
        except Exception:
            self.business_conn.rollback()
            logger.error("User %s created but default workspace creation failed", user_id, exc_info=True)

        return user_id

    def update_password(self, user_id, hashed_password, version=1):
        c = self.conn.cursor()
        try:
            has_password_version = self._has_column(c, 'users', 'password_version')
            if has_password_version:
                c.execute(
                    'UPDATE users SET password = ?, password_version = ? WHERE id = ?',
                    (hashed_password, version, user_id)
                )
            else:
                c.execute(
                    'UPDATE users SET password = ? WHERE id = ?',
                    (hashed_password, user_id)
                )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error("Failed to update password for user %s: %s", user_id, e)
            self.conn.rollback()
            return False

    def get_user_workspaces(self, user_id):
        c = self.conn.cursor()
        try:
            # Real Postgres schema uses `status` (text, e.g. 'active'); only
            # the SQLite dev-schema block has `is_active` (int) — pre-existing
            # drift between the two, unrelated to which DB this connects to.
            c.execute(
                'SELECT id, user_id, name, type, description, is_active, created_at'
                ' FROM workspaces WHERE user_id = ? ORDER BY created_at',
                (user_id,),
            )
            return c.fetchall()
        except Exception:
            self.conn.rollback()
            c = self.conn.cursor()
            c.execute(
                'SELECT id, user_id, name, type, description, status, created_at'
                ' FROM workspaces WHERE user_id = ? ORDER BY created_at',
                (user_id,),
            )
            return c.fetchall()

    def get_all_users_with_permissions(self):
        c = self.conn.cursor()
        c.execute("SELECT u.id, u.name, u.email, u.role FROM users u")
        return [
            {'id': row['id'], 'name': row['name'], 'email': row['email'],
             'role': row['role'], 'permissions': []}
            for row in c.fetchall()
        ]

    def get_all_users(self, role_filter=None):
        c = self.conn.cursor()
        query = 'SELECT id, email, first_name, last_name, role, created_at FROM users'
        params = []
        if role_filter:
            query += ' WHERE role = ?'
            params.append(role_filter)
        query += ' ORDER BY created_at DESC'
        
        try:
            c.execute(query, tuple(params))
        except Exception:
            # Fallback for legacy schema
            query = query.replace('first_name, last_name', 'name')
            c.execute(query, tuple(params))
            
        return [self._standardize_user(row, include_created_at=True) for row in c.fetchall()]

    def get_users_for_manager(self, manager_id, role_filter=None):
        c = self.conn.cursor()
        query = 'SELECT id, email, first_name, last_name, role, created_at FROM users WHERE manager_id = ?'
        params = [manager_id]
        if role_filter:
            query += ' AND role = ?'
            params.append(role_filter)
        query += ' ORDER BY created_at DESC'
        
        try:
            c.execute(query, tuple(params))
        except Exception:
            # Fallback for legacy schema
            query = query.replace('first_name, last_name', 'name')
            c.execute(query, tuple(params))
            
        return [self._standardize_user(row, include_created_at=True) for row in c.fetchall()]

    def delete_user(self, user_id):
        c = self.conn.cursor()
        try:
            c.execute('DELETE FROM users WHERE id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            raise

    def set_user_role(self, user_id, new_role):
        c = self.conn.cursor()
        try:
            c.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            raise

    def update_google_account(self, user_id, token_json, google_email, avatar=None):
        c = self.conn.cursor()
        try:
            columns = ['google_token = ?']
            values = [token_json]
            if self._has_column(c, 'users', 'google_email'):
                columns.append('google_email = ?')
                values.append(google_email)
            if avatar is not None and self._has_column(c, 'users', 'avatar'):
                columns.append('avatar = ?')
                values.append(avatar)
            values.append(user_id)
            c.execute(f"UPDATE users SET {', '.join(columns)} WHERE id = ?", tuple(values))
            self.conn.commit()
            return c.rowcount > 0
        except Exception:
            self.conn.rollback()
            raise

    def upsert_google_user(self, email, name, avatar, token_json, hashed_password):
        c = self.conn.cursor()
        try:
            c.execute('SELECT id, role, email FROM users WHERE email = ?', (email,))
            row = c.fetchone()
            if row is None and self._has_column(c, 'users', 'google_email'):
                c.execute('SELECT id, role, email FROM users WHERE google_email = ?', (email,))
                row = c.fetchone()

            if row:
                user_id = row['id']
                self.update_google_account(user_id, token_json, email, avatar)
                return {
                    'id': user_id,
                    'role': row['role'],
                    'created': False,
                    'first_name': (name.split(' ')[0] if name else 'Google'),
                }

            names = (name or 'Google User').split(' ')
            first_name = names[0]
            last_name = ' '.join(names[1:]) if len(names) > 1 else ''

            cols = ['email', 'password', 'name', 'role']
            vals = [email, hashed_password, name, 'manager']
            placeholders = ['?', '?', '?', '?']

            optional_values = {
                'first_name': first_name,
                'last_name': last_name,
                'avatar': avatar,
                'google_token': token_json,
                'google_email': email,
                'password_version': 1,
            }
            for column, value in optional_values.items():
                if self._has_column(c, 'users', column):
                    cols.append(column)
                    vals.append(value)
                    placeholders.append('?')

            c.execute(
                f"INSERT INTO users ({', '.join(cols)}) VALUES ({', '.join(placeholders)})",
                tuple(vals),
            )
            user_id = c.lastrowid
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

        try:
            bc = self.business_conn.cursor()
            bc.execute(
                'INSERT INTO workspaces (user_id, name, type, description) VALUES (?, ?, ?, ?)',
                (user_id, f"{first_name}'s Personal Workspace", 'personal',
                 'Your personal productivity space'),
            )
            self.business_conn.commit()
        except Exception:
            self.business_conn.rollback()
            logger.error("Google user %s created but default workspace creation failed", user_id, exc_info=True)

        return {'id': user_id, 'role': 'manager', 'created': True, 'first_name': first_name}

    # ── helpers ──────────────────────────────────────────────────────────────

    def _standardize_user(self, row, include_password=False, include_created_at=False):
        """Standardize user dictionary schema."""
        if not isinstance(row, dict):
            row = {k: row[k] for k in row.keys()}
        # Handle cases where name might be full name or just first name
        name = row.get('name', '')
        first_name = row.get('first_name')
        last_name = row.get('last_name')

        if first_name is None:
            # Try to split name if first_name is missing in DB
            parts = name.split()
            first_name = parts[0] if parts else ''
            last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

        user = {
            'id': row['id'],
            'email': row['email'],
            'first_name': first_name,
            'last_name': last_name,
            'name': f"{first_name} {last_name}".strip(),
            'role': row.get('role', 'user'),
            'google_token': row.get('google_token'),
            'avatar': row.get('avatar'),
        }

        if include_created_at:
            user['created_at'] = row.get('created_at')

        if include_password:
            user['password'] = row.get('password')
            user['password_version'] = row.get('password_version', 0)

        return user

    def _has_column(self, cursor, table, column) -> bool:
        try:
            if _is_postgres(self.conn):
                # PostgreSQL uses lower case for table names in information_schema
                cursor.execute(
                    "SELECT 1 FROM information_schema.columns"
                    " WHERE table_name = %s AND column_name = %s",
                    (table.lower(), column.lower()),
                )
            else:
                cursor.execute(f"PRAGMA table_info({table})")
                return any(row['name'] == column for row in cursor.fetchall())
            return cursor.fetchone() is not None
        except Exception as e:
            logger.debug("Error checking column %s in table %s: %s", column, table, e)
            return False
