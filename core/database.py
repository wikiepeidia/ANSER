import sqlite3
import re
import threading
from datetime import datetime
from .config import Config
import bcrypt
from core.logger import get_logger

logger = get_logger(__name__)

# Compatibility shim
try:
    from app.db import SessionLocal, Base
except Exception:
    SessionLocal = None
    Base = None

# Matches single-quoted strings, double-quoted identifiers, or a standalone ?.
# Alternation is left-to-right: quoted content is consumed first so any ?
# inside quotes never reaches the capture group.
_PG_PLACEHOLDER_RE = re.compile(
    r"'(?:[^'\\]|\\.)*'"   # single-quoted string literal
    r'|"(?:[^"\\]|\\.)*"'  # double-quoted identifier
    r'|(\?)',               # standalone parameter placeholder
    re.DOTALL,
)


def _to_pg(query: str) -> str:
    """Replace SQLite ? placeholders with psycopg2 %s, skipping ? inside quoted strings."""
    return _PG_PLACEHOLDER_RE.sub(
        lambda m: '%s' if m.group(1) is not None else m.group(0),
        query,
    )


class PGShimCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None
        self.rowcount = -1

    def execute(self, query, params=None):
        has_params = params is not None and len(params) > 0
        query = _to_pg(query)
        is_insert = query.strip().upper().startswith('INSERT')
        try:
            if is_insert and 'RETURNING' not in query.upper():
                query += " RETURNING id"
                self._cursor.execute(query, params) if has_params else self._cursor.execute(query)
                row = self._cursor.fetchone()
                if row: self.lastrowid = row['id']
            else:
                self._cursor.execute(query, params) if has_params else self._cursor.execute(query)
                self.lastrowid = None
            self.rowcount = self._cursor.rowcount
            return self
        except Exception as e:
            if is_insert and 'RETURNING id' in query:
                try:
                    if hasattr(self._cursor, 'connection'): self._cursor.connection.rollback()
                except Exception:
                    pass
                clean_query = query.replace(" RETURNING id", "")
                self._cursor.execute(clean_query, params) if has_params else self._cursor.execute(clean_query)
                self.lastrowid = None
                return self
            raise e

    def executemany(self, query, params_seq):
        query = _to_pg(query)
        self._cursor.executemany(query, params_seq)
        return self

    def fetchone(self): return self._cursor.fetchone()
    def fetchall(self): return self._cursor.fetchall()
    def fetchmany(self, size=None): return self._cursor.fetchmany(size)
    def close(self): self._cursor.close()
    def __getattr__(self, name): return getattr(self._cursor, name)

class PGShimConnection:
    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool
        self._closed = False
        self.row_factory = None

    def cursor(self):
        import psycopg2.extras
        return PGShimCursor(self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor))

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._conn.rollback()  # return conn to pool in clean state
        except Exception:
            pass
        if self._pool is not None:
            self._pool.putconn(self._conn)
        else:
            self._conn.close()

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.use_postgres = getattr(Config, 'USE_POSTGRES', False)
        self._pg_pool = None
        self._pg_pool_lock = threading.Lock()
        if not self.use_postgres:
            self.init_database()

    def _get_pg_pool(self):
        """Lazily create the PostgreSQL connection pool on first use."""
        if self._pg_pool is not None:
            return self._pg_pool
        with self._pg_pool_lock:
            if self._pg_pool is None:
                import psycopg2.pool
                self._pg_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=Config.POSTGRES_URL,
                )
                logger.info("PostgreSQL connection pool initialized (min=1, max=10)")
        return self._pg_pool

    def get_table_columns(self, table_name, cursor=None):
        should_close = False
        if cursor is None:
            conn = self.get_connection()
            cursor = conn.cursor()
            should_close = True
        try:
            if self.use_postgres:
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table_name,))
                columns = [row['column_name'] for row in cursor.fetchall()]
            else:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row['name'] for row in cursor.fetchall()]
            return columns
        finally:
            if should_close:
                try: cursor.close()
                except Exception: pass
                try: conn.close()
                except Exception: pass

    def get_connection(self):
        if self.use_postgres:
            pool = self._get_pg_pool()
            raw = pool.getconn()
            return PGShimConnection(raw, pool)
        else:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            return conn
    
    def init_database(self):
        """Create SQLite schema for local development.

        PostgreSQL (NeonDB) schema is managed by Alembic — run:
            python -m alembic upgrade head
        """
        conn = self.get_connection()
        c = conn.cursor()
        c.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                password_version INTEGER DEFAULT 0,
                name TEXT,
                role TEXT DEFAULT 'user',
                avatar TEXT,
                theme TEXT DEFAULT 'dark',
                first_name TEXT,
                last_name TEXT,
                google_token TEXT,
                manager_id INTEGER,
                subscription_expires_at TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT DEFAULT 'personal',
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                type TEXT DEFAULT 'task',
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'medium',
                assignee_id INTEGER,
                due_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT,
                notes TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                category TEXT,
                unit TEXT,
                price REAL DEFAULT 0,
                stock_quantity INTEGER DEFAULT 0,
                description TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                image_url TEXT
            );
            CREATE TABLE IF NOT EXISTS import_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                supplier_name TEXT,
                total_amount REAL DEFAULT 0,
                notes TEXT,
                status TEXT DEFAULT 'completed',
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS import_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_id INTEGER NOT NULL,
                product_id INTEGER,
                quantity REAL DEFAULT 0,
                unit_price REAL DEFAULT 0,
                total_price REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS export_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                customer_name TEXT,
                total_amount REAL DEFAULT 0,
                notes TEXT,
                status TEXT DEFAULT 'completed',
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS export_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                export_id INTEGER NOT NULL,
                product_id INTEGER,
                quantity REAL DEFAULT 0,
                unit_price REAL DEFAULT 0,
                total_price REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                total_amount REAL,
                amount_given REAL,
                change_amount REAL,
                items TEXT,
                payment_method TEXT DEFAULT 'cash',
                workspace_id INTEGER,
                category TEXT DEFAULT 'Retail',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS manager_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                subscription_type TEXT,
                amount REAL,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'inactive',
                auto_renew INTEGER DEFAULT 0,
                payment_method TEXT,
                transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS subscription_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                subscription_type TEXT,
                amount REAL,
                payment_date TEXT,
                payment_method TEXT,
                transaction_id TEXT,
                status TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                balance REAL DEFAULT 0,
                currency TEXT DEFAULT 'VND',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                currency TEXT DEFAULT 'VND',
                type TEXT,
                status TEXT DEFAULT 'pending',
                method TEXT,
                reference TEXT,
                notes TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                description TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS se_automations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                type TEXT,
                config TEXT,
                enabled INTEGER DEFAULT 0,
                last_run TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS scheduled_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                report_type TEXT,
                frequency TEXT,
                channel TEXT,
                recipients TEXT,
                status TEXT DEFAULT 'active',
                last_sent_at TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                details TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ai_chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                workspace_id INTEGER,
                title TEXT,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chat_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                file_name TEXT,
                file_type TEXT,
                analysis_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                group_name TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        conn.commit()
        conn.close()

    # --- USER & CORE METHODS (Keep your existing ones) ---
    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute('SELECT id, email, name, avatar, theme, role, first_name, last_name, google_token FROM users WHERE id = ?', (user_id,))
            user = c.fetchone()
            if user:
                return {
                    'id': user['id'],
                    'email': user['email'],
                    'name': user['name'],
                    'avatar': user['avatar'],
                    'theme': user['theme'],
                    'role': user['role'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'google_token': user['google_token'],
                }
        except Exception:
            # Fallback for old schema missing extended columns
            try:
                c.execute('SELECT id, email, name, avatar, theme, role FROM users WHERE id = ?', (user_id,))
                user = c.fetchone()
                if user:
                    return {
                        'id': user['id'],
                        'email': user['email'],
                        'name': user['name'],
                        'avatar': user['avatar'],
                        'theme': user['theme'],
                        'role': user['role'],
                        'first_name': None,
                        'last_name': None,
                        'google_token': None,
                    }
            except Exception:
                pass
        finally:
            conn.close()
        return None

    def create_user(self, email, password, name, role="user", first_name=None, last_name=None, manager_id=None):
        conn = self.get_connection()
        c = conn.cursor()
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            columns = self.get_table_columns("users", cursor=c)
            if 'first_name' in columns:
                c.execute('INSERT INTO users (email, password, password_version, name, role, first_name, last_name, manager_id) VALUES (?, ?, 1, ?, ?, ?, ?, ?)',
                         (email, hashed_pw, name, role, first_name, last_name, manager_id))
            else:
                c.execute('INSERT INTO users (email, password, password_version, name, role, manager_id) VALUES (?, ?, 1, ?, ?, ?)',
                         (email, hashed_pw, name, role, manager_id))
            user_id = c.lastrowid
            conn.commit()
            return user_id
        except Exception as e:
            if "UNIQUE constraint" in str(e) or "duplicate key" in str(e): raise Exception('Email exists')
            raise e
        finally: conn.close()

    def verify_user(self, email, password):
        # ... (Keep existing verify_user) ...
        pass

    def get_user_workspaces(self, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute(
            'SELECT id, user_id, name, type, description, is_active, created_at'
            ' FROM workspaces WHERE user_id = ? ORDER BY created_at',
            (user_id,),
        )
        workspaces = c.fetchall()
        conn.close()
        return workspaces

    def get_all_users_with_permissions(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''SELECT u.id, u.name, u.email, u.role, '' as permissions FROM users u''')
        users = []
        for row in c.fetchall():
            users.append({'id': row['id'], 'name': row['name'], 'email': row['email'], 'role': row['role'], 'permissions': []})
        conn.close()
        return users
        
    def get_recent_activities(self, limit=20):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute(
                'SELECT id, user_id, action, details, ip_address, created_at '
                'FROM activity_logs ORDER BY created_at DESC LIMIT ?', (limit,)
            )
            return [
                {'id': r['id'], 'user_id': r['user_id'], 'action': r['action'],
                 'details': r['details'], 'ip_address': r['ip_address'], 'created_at': r['created_at']}
                for r in c.fetchall()
            ]
        except Exception:
            return []
        finally:
            conn.close()

    def log_activity(self, user_id, action, details=None, ip_address=None):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            c.execute('INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
                     (user_id, action, details, ip_address))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    # --- AI MEMORY METHODS (FIXED) ---
    def add_ai_message(self, user_id, role, content):
        """Saves a message to the Cloud DB (Neon) using 'created_at'"""
        conn = self.get_connection()
        c = conn.cursor()
        try:
            # FIX: Using 'created_at' to match the new schema
            c.execute('INSERT INTO ai_chat_history (user_id, role, content, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)', 
                     (user_id, role, content))
            conn.commit()
        except Exception as e:
            logger.error("Memory save error for user %s: %s", user_id, e, exc_info=True)
        finally:
            conn.close()

    def get_ai_history(self, user_id, limit=6):
        """Fetches recent context from Cloud DB (Neon)"""
        conn = self.get_connection()
        c = conn.cursor()
        try:
            # FIX: Ordering by 'created_at'
            c.execute('''SELECT role, content FROM ai_chat_history 
                         WHERE user_id = ? 
                         ORDER BY created_at DESC LIMIT ?''', (user_id, limit))
            rows = c.fetchall()
            
            history = []
            for r in reversed(rows):
                role_name = "User" if r['role'] == 'user' else "AI"
                history.append(f"{role_name}: {r['content']}")
            
            return "\n".join(history)
        except Exception as e:
            logger.error("Memory fetch error for user %s: %s", user_id, e, exc_info=True)
            return ""
        finally:
            conn.close()

    def save_attachment(self, user_id, workspace_id, filename, filetype, analysis):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            # Get or Create Session
            c.execute("SELECT id FROM chat_sessions WHERE user_id = ? ORDER BY last_active DESC LIMIT 1", (user_id,))
            row = c.fetchone()
            if row:
                sid = row['id']
            else:
                if self.use_postgres:
                    c.execute("INSERT INTO chat_sessions (user_id, workspace_id, title) VALUES (%s, %s, 'New Chat') RETURNING id", (user_id, workspace_id))
                    sid = c.fetchone()['id']
                else:
                    c.execute("INSERT INTO chat_sessions (user_id, workspace_id, title) VALUES (?, ?, 'New Chat')", (user_id, workspace_id))
                    sid = c.lastrowid

            # Insert Attachment
            if self.use_postgres:
                c.execute("INSERT INTO chat_attachments (session_id, file_name, file_type, analysis_summary, created_at) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)", 
                         (sid, filename, filetype, analysis))
            else:
                c.execute("INSERT INTO chat_attachments (session_id, file_name, file_type, analysis_summary) VALUES (?, ?, ?, ?)", 
                         (sid, filename, filetype, analysis))
            
            conn.commit()
        except Exception as e:
            logger.error("DB attachment save error for user %s, file %s: %s", user_id, filename, e, exc_info=True)
        finally:
            conn.close()

    # --- WORKFLOW METHODS (FIXED) ---
    def create_workflow(self, user_id, name, data):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO workflows (user_id, name, data, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)',
                     (user_id, name, data))
            wf_id = c.lastrowid
            conn.commit()
            return wf_id
        finally:
            conn.close()

    def get_scenarios(self, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT id, name, description, updated_at, data FROM workflows WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
            rows = c.fetchall()
            scenarios = []
            for row in rows:
                scenarios.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'updated_at': row['updated_at'],
                    'data': row['data'],
                    'steps': row['data'],
                })
            return scenarios
        except Exception as e:
            logger.error("Error fetching scenarios for user %s: %s", user_id, e, exc_info=True)
            return []
        finally:
            conn.close()

    def get_scenario(self, scenario_id, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT id, name, description, updated_at, data, user_id FROM workflows WHERE id = ? AND user_id = ?", (scenario_id, user_id))
            row = c.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'updated_at': row['updated_at'],
                    'data': row['data'],
                    'steps': row['data'],
                    'user_id': row['user_id'],
                }
            return None
        finally:
            conn.close()

    def create_scenario(self, user_id, name, description, active, steps):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            # Note: 'active' column does not exist in the schema, ignoring it.
            c.execute('INSERT INTO workflows (user_id, name, description, data, created_at, updated_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)',
                     (user_id, name, description, steps))
            scenario_id = c.lastrowid
            conn.commit()
            return scenario_id
        finally:
            conn.close()

    def update_scenario(self, scenario_id, user_id, data):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            name = data.get('name')
            description = data.get('description')
            steps = data.get('steps')
            
            updates = []
            values = []
            
            if name is not None:
                updates.append("name = ?")
                values.append(name)
            if description is not None:
                updates.append("description = ?")
                values.append(description)
            if steps is not None:
                updates.append("data = ?")
                values.append(steps)
            
            if not updates:
                return

            updates.append("updated_at = CURRENT_TIMESTAMP")
            
            query = f"UPDATE workflows SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
            values.extend([scenario_id, user_id])
            
            c.execute(query, tuple(values))
            conn.commit()
        finally:
            conn.close()

    def delete_scenario(self, scenario_id, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute("DELETE FROM workflows WHERE id = ? AND user_id = ?", (scenario_id, user_id))
            conn.commit()
        finally:
            conn.close()

