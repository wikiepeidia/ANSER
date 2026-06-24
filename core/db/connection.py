<<<<<<< HEAD
"""Database connection factory, PGShim adapter, and facade Database class."""
import sqlite3
import re
import threading
from contextlib import contextmanager

from core.config import Config
from core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# PostgreSQL placeholder conversion
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# PGShim — bridges sqlite3-style API with psycopg2
# ---------------------------------------------------------------------------

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
                if row:
                    self.lastrowid = row['id']
            else:
                self._cursor.execute(query, params) if has_params else self._cursor.execute(query)
                self.lastrowid = None
            self.rowcount = self._cursor.rowcount
            return self
        except Exception as e:
            if is_insert and 'RETURNING id' in query:
                try:
                    if hasattr(self._cursor, 'connection'):
                        self._cursor.connection.rollback()
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

    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self._conn.rollback()
        except Exception:
            pass
        if self._pool is not None:
            self._pool.putconn(self._conn)
        else:
            self._conn.close()


# ---------------------------------------------------------------------------
# Database — connection factory + pool + facade delegating to repos
# ---------------------------------------------------------------------------

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.use_postgres = getattr(Config, 'USE_POSTGRES', False)
        self._pg_pool = None
        self._pg_pool_lock = threading.Lock()
        if not self.use_postgres:
            self.init_database()

    # ── Connection pool ───────────────────────────────────────────────────

    def _get_pg_pool(self):
        if self._pg_pool is not None:
            return self._pg_pool
        with self._pg_pool_lock:
            if self._pg_pool is None:
                import psycopg2.pool
                self._pg_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=2, maxconn=10, dsn=Config.POSTGRES_URL,
                )
                logger.info("PostgreSQL connection pool initialized (min=2, max=10)")
        return self._pg_pool

    def get_connection(self):
        if self.use_postgres:
            pool = self._get_pg_pool()
            return PGShimConnection(pool.getconn(), pool)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def get_db_connection(self):
        """Yield a connection and guarantee it's returned to the pool on exit."""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            conn.close()

    def get_table_columns(self, table_name, cursor=None):
        should_close = False
        if cursor is None:
            conn = self.get_connection()
            cursor = conn.cursor()
            should_close = True
        try:
            if self.use_postgres:
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                    (table_name,),
                )
                return [row['column_name'] for row in cursor.fetchall()]
            else:
                cursor.execute(f"PRAGMA table_info({table_name})")
                return [row['name'] for row in cursor.fetchall()]
        finally:
            if should_close:
                try: cursor.close()
                except Exception: pass
                try: conn.close()
                except Exception: pass

    def init_database(self):
        """Create SQLite schema for local development.

        PostgreSQL (NeonDB) schema is managed by Alembic:
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
                customer_id INTEGER,
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

    # ── has_permission (used by auth decorator) ────────────────────────────

    def has_permission(self, user_id, permission_type):
        return False  # placeholder — permissions via role for now

    # ── Facade — delegate to repos ─────────────────────────────────────────
    # Each method opens a connection, constructs the repo, delegates, closes.

    def _user_repo(self, conn):
        from core.db.user_repo import UserRepo
        return UserRepo(conn)

    def _activity_repo(self, conn):
        from core.db.activity_repo import ActivityRepo
        return ActivityRepo(conn)

    def _chat_repo(self, conn):
        from core.db.chat_repo import ChatRepo
        return ChatRepo(conn)

    def _workflow_repo(self, conn):
        from core.db.workflow_repo import WorkflowRepo
        return WorkflowRepo(conn)

    # User

    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        try:
            return self._user_repo(conn).get_user_by_id(user_id)
        finally:
            conn.close()

    def get_user_by_email(self, email):
        conn = self.get_connection()
        try:
            return self._user_repo(conn).get_user_by_email(email)
        finally:
            conn.close()

    def create_user(self, email, password, first_name, last_name, role='user', manager_id=None):
        conn = self.get_connection()
        try:
            return self._user_repo(conn).create_user(
                email, password, first_name, last_name, role, manager_id,
            )
        finally:
            conn.close()

    def update_password(self, user_id, hashed_password, version=1):
        conn = self.get_connection()
        try:
            return self._user_repo(conn).update_password(user_id, hashed_password, version)
        finally:
            conn.close()

    # verify_user is handled by AuthManager.verify_user in core/auth.py

    def get_user_workspaces(self, user_id):
        conn = self.get_connection()
        try:
            return self._user_repo(conn).get_user_workspaces(user_id)
        finally:
            conn.close()

    def get_all_users_with_permissions(self):
        conn = self.get_connection()
        try:
            return self._user_repo(conn).get_all_users_with_permissions()
        finally:
            conn.close()

    def get_all_users(self, role_filter=None):
        conn = self.get_connection()
        try:
            return self._user_repo(conn).get_all_users(role_filter)
        finally:
            conn.close()

    def get_users_for_manager(self, manager_id, role_filter=None):
        conn = self.get_connection()
        try:
            return self._user_repo(conn).get_users_for_manager(manager_id, role_filter)
        finally:
            conn.close()

    def delete_user(self, user_id):
        conn = self.get_connection()
        try:
            return self._user_repo(conn).delete_user(user_id)
        finally:
            conn.close()

    def set_user_role(self, user_id, new_role):
        conn = self.get_connection()
        try:
            return self._user_repo(conn).set_user_role(user_id, new_role)
        finally:
            conn.close()

    # Activity

    def get_recent_activities(self, limit=20):
        conn = self.get_connection()
        try:
            return self._activity_repo(conn).get_recent_activities(limit)
        finally:
            conn.close()

    def log_activity(self, user_id, action, details=None, ip_address=None):
        try:
            conn = self.get_connection()
            try:
                self._activity_repo(conn).log_activity(user_id, action, details, ip_address)
                return True
            finally:
                conn.close()
        except Exception:
            return False

    # AI Chat

    def add_ai_message(self, user_id, role, content):
        conn = self.get_connection()
        try:
            self._chat_repo(conn).add_ai_message(user_id, role, content)
        finally:
            conn.close()

    def get_ai_history(self, user_id, limit=6):
        conn = self.get_connection()
        try:
            return self._chat_repo(conn).get_ai_history(user_id, limit)
        finally:
            conn.close()

    def save_attachment(self, user_id, workspace_id, filename, filetype, analysis):
        conn = self.get_connection()
        try:
            self._chat_repo(conn).save_attachment(user_id, workspace_id, filename, filetype, analysis)
        finally:
            conn.close()

    # Workflow / Scenario

    def create_workflow(self, user_id, name, data):
        conn = self.get_connection()
        try:
            return self._workflow_repo(conn).create_workflow(user_id, name, data)
        finally:
            conn.close()

    def get_scenarios(self, user_id):
        conn = self.get_connection()
        try:
            return self._workflow_repo(conn).get_scenarios(user_id)
        finally:
            conn.close()

    def get_scenario(self, scenario_id, user_id):
        conn = self.get_connection()
        try:
            return self._workflow_repo(conn).get_scenario(scenario_id, user_id)
        finally:
            conn.close()

    def create_scenario(self, user_id, name, description, active, steps):
        conn = self.get_connection()
        try:
            return self._workflow_repo(conn).create_scenario(user_id, name, description, active, steps)
        finally:
            conn.close()

    def update_scenario(self, scenario_id, user_id, data):
        conn = self.get_connection()
        try:
            self._workflow_repo(conn).update_scenario(scenario_id, user_id, data)
        finally:
            conn.close()

    def delete_scenario(self, scenario_id, user_id):
        conn = self.get_connection()
        try:
            self._workflow_repo(conn).delete_scenario(scenario_id, user_id)
        finally:
            conn.close()
=======
"""
Database connection for NeonDB (PostgreSQL).
Schema is managed exclusively by Alembic — do NOT create or alter tables manually.
Run migrations with: alembic upgrade head
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

_raw_url = os.environ["POSTGRES_URL"]
# SQLAlchemy requires postgresql+psycopg2:// driver prefix
DB_URL = _raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
>>>>>>> f7fef83fb139ef6abcb07c2a02a10f7512378a9e
