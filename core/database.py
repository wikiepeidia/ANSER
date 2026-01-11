import sqlite3
import hashlib
import re
from datetime import datetime
from .config import Config

# Compatibility shim: if `app.db` exists, expose SessionLocal and Base for other modules
try:
    from app.db import SessionLocal, Base  # type: ignore
except Exception:
    SessionLocal = None
    Base = None

# Postgres Adapter Classes
class PGShimCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None
        self.rowcount = -1

    def execute(self, query, params=None):
        if params is None:
            params = ()
        
        # 1. Convert ? placeholders to %s
        query = query.replace('?', '%s')
        
        # 2. Handle Auto-increment IDs (sqlite's lastrowid)
        # We append RETURNING id if it's an INSERT and look for the result
        is_insert = query.strip().upper().startswith('INSERT')
        
        try:
            if is_insert and 'RETURNING' not in query.upper():
                query += " RETURNING id"
                self._cursor.execute(query, params)
                row = self._cursor.fetchone()
                if row:
                    self.lastrowid = row[0]
            else:
                self._cursor.execute(query, params)
                self.lastrowid = None
            
            self.rowcount = self._cursor.rowcount
            return self
        except Exception as e:
            # If RETURNING id failed (maybe table has no id column?), try without it
            if is_insert and 'RETURNING id' in query:
                # print(f"Postgres Shim Info: 'RETURNING id' failed ({e}). Rolling back and retrying without it.")
                try:
                    # Try to access connection and rollback
                    if hasattr(self._cursor, 'connection'):
                         self._cursor.connection.rollback()
                    else:
                         # Fallback if cursor doesn't have connection attribute directly
                         print("Postgres Shim Warning: Cannot access cursor.connection to rollback.")
                except Exception as rb_error:
                     print(f"Postgres Shim Error: Rollback failed during retry: {rb_error}")

                clean_query = query.replace(" RETURNING id", "")
                try:
                    self._cursor.execute(clean_query, params)
                    self.lastrowid = None
                    return self
                except Exception as retry_error:
                    # If retry fails, raise the RETRY error (likely the same fundamental issue), or logic to bubble up original
                     # print(f"Postgres Shim: Retry also failed: {retry_error}")
                     raise retry_error
            raise e

    def executemany(self, query, params_seq):
        query = query.replace('?', '%s')
        self._cursor.executemany(query, params_seq)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()
        
    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size)
    
    def close(self):
        self._cursor.close()

    def __getattr__(self, name):
        return getattr(self._cursor, name)

class PGShimConnection:
    def __init__(self, conn):
        self._conn = conn
        self.row_factory = None # Not fully implemented

    def cursor(self):
        return PGShimCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.use_postgres = getattr(Config, 'USE_POSTGRES', False)
        # We do NOT allow init_database to run automatically on import if using Postgres
        # to prevent accidental schema changes. Migration script should handle it.
        if not self.use_postgres:
            self.init_database()
        # If postgres, we assume schema is managed or we call init manually if needed
        # But for safety in this hybrid state, let's allow it to run once to ensure tables exist
        if self.use_postgres:
            try:
                self.init_database()
            except Exception as e:
                print(f"Postgres Init Warning: {e}") 

    def get_table_columns(self, table_name, cursor=None):
        """Get list of columns for a table, DB-agnostic"""
        should_close = False
        if cursor is None:
            conn = self.get_connection()
            cursor = conn.cursor()
            should_close = True
            
        try:
            if self.use_postgres:
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table_name,))
                columns = [row[0] for row in cursor.fetchall()]
            else:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
            return columns
        finally:
            if should_close:
                # For PGShimConnection, close() closes the real connection
                # For sqlite3, close() on cursor is good, connection verify
                try:
                    cursor.close()
                    if hasattr(cursor, 'connection') and cursor.connection:
                         cursor.connection.close()
                except:
                    pass

    def get_connection(self):
        if self.use_postgres:
            import psycopg2
            conn = psycopg2.connect(Config.POSTGRES_URL)
            return PGShimConnection(conn)
        else:
             # Increase timeout to 30 seconds to avoid "database is locked" errors
            return sqlite3.connect(self.db_path, timeout=30.0)
    
    def init_database(self):
        conn = self.get_connection()
        c = conn.cursor()
        
        # Postgres Shim Note:
        # The CREATE TABLE syntax is mostly compatible, but AUTOINCREMENT is not.
        # SQLite: INTEGER PRIMARY KEY AUTOINCREMENT
        # Postgres: SERIAL PRIMARY KEY (Handled by migration script or manual fix)
        # However, since we are using IF NOT EXISTS, we can leave the SQLite syntax 
        # IF we handle the translation in the execute() method? No, execute() only handles dml.
        # DDL differences are significant.
        # For this hybrid `init_database`, we should detect engine and use appropriate SQL.
        
        is_pg = self.use_postgres
        
        if is_pg:
            # Postgres Init Logic (Simplified)
            # This is complex because we have many CREATE statements.
            # Ideally, use the migration tool to init.
            # We will just pass here if tables exist, or run a simplified check.
            pass # We rely on 'python database/progres.py' to init schema for Postgres
        else:
            # SQLite Init Logic (Original)
            self._init_sqlite(c)
            conn.commit()
        
        conn.close()

    def _init_sqlite(self, c):
        # Users table (có cột role)
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            avatar TEXT,
            theme TEXT DEFAULT 'dark',
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # If the old table doesn't have a 'role' column, add it
        columns = self.get_table_columns("users", cursor=c)
        if 'role' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        
        if 'google_token' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN google_token TEXT")

        if 'google_email' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN google_email TEXT")
            
        if 'manager_id' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN manager_id INTEGER REFERENCES users(id)")
        
        # Workspaces table
        c.execute('''CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            settings TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')
        
        # Tasks/Items table
        c.execute('''CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            type TEXT DEFAULT 'task',
            status TEXT DEFAULT 'todo',
            priority TEXT DEFAULT 'medium',
            assignee_id INTEGER,
            parent_id INTEGER,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workspace_id) REFERENCES workspaces (id),
            FOREIGN KEY (assignee_id) REFERENCES users (id),
            FOREIGN KEY (parent_id) REFERENCES items (id)
        )''')
        
        # Scenarios table
        c.execute('''CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            steps TEXT,
            conditions TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workspace_id) REFERENCES workspaces (id)
        )''')
        
        # Sales table
        c.execute('''CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            workspace_id INTEGER,
            total_amount REAL,
            amount_given REAL,
            change_amount REAL,
            items TEXT,
            payment_method TEXT DEFAULT 'cash',
            category TEXT DEFAULT 'Retail',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')
        
        # Communication channels
        c.execute('''CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_workspace_id INTEGER,
            to_workspace_id INTEGER,
            channel_type TEXT NOT NULL,
            config TEXT,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_workspace_id) REFERENCES workspaces (id),
            FOREIGN KEY (to_workspace_id) REFERENCES workspaces (id)
        )''')
        
        # User permissions table
        c.execute('''CREATE TABLE IF NOT EXISTS user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            permission_type TEXT NOT NULL,
            granted_by INTEGER,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            revoked BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (granted_by) REFERENCES users (id),
            UNIQUE(user_id, permission_type)
        )''')

        # System Settings table
        c.execute('''CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            group_name TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Initialize default settings if empty
        c.execute("SELECT count(*) FROM system_settings")
        if c.fetchone()[0] == 0:
            defaults = [
                ('store_name', 'My AI Store', 'store'),
                ('store_address', '123 AI Blvd', 'store'),
                ('currency', 'VND', 'store'),
                ('ocr_confidence', '0.8', 'ai'),
                ('auto_import_threshold', '0.9', 'ai'),
                ('enable_low_stock_alerts', 'true', 'notifications'),
                ('low_stock_threshold', '10', 'notifications'),
                ('notification_email', 'admin@example.com', 'notifications'),
                ('backup_frequency', 'daily', 'system'),
                ('keep_images_days', '30', 'system')
            ]
            c.executemany("INSERT INTO system_settings (key, value, group_name) VALUES (?, ?, ?)", defaults)

        # Activity Logs table
        c.execute('''CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')

        # Workflows table
        c.execute('''CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )''')
        
        # Customers table (Khách hàng)
        c.execute('''CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )''')
        
        # Products table (Sản phẩm)
        c.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            unit TEXT DEFAULT 'cái',
            price REAL DEFAULT 0,
            stock_quantity INTEGER DEFAULT 0,
            description TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )''')
        
        # Import transactions (Nhập hàng)
        c.execute('''CREATE TABLE IF NOT EXISTS import_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            supplier_name TEXT,
            total_amount REAL DEFAULT 0,
            notes TEXT,
            status TEXT DEFAULT 'completed',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )''')
        
        # Import transaction details
        c.execute('''CREATE TABLE IF NOT EXISTS import_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (import_id) REFERENCES import_transactions (id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )''')
        
        # Export transactions (Xuất hàng)
        c.execute('''CREATE TABLE IF NOT EXISTS export_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            customer_id INTEGER,
            total_amount REAL DEFAULT 0,
            notes TEXT,
            status TEXT DEFAULT 'completed',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )''')
        
        # Export transaction details
        c.execute('''CREATE TABLE IF NOT EXISTS export_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            export_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (export_id) REFERENCES export_transactions (id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )''')
        
        # SE Automation configs (Scenarios & Events)
        c.execute('''CREATE TABLE IF NOT EXISTS se_automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            config TEXT,
            enabled BOOLEAN DEFAULT 1,
            last_run TIMESTAMP,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )''')

        # Scheduled Reports
        c.execute('''CREATE TABLE IF NOT EXISTS scheduled_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            report_type TEXT NOT NULL,
            frequency TEXT NOT NULL,
            channel TEXT NOT NULL,
            recipients TEXT,
            status TEXT DEFAULT 'active',
            last_sent_at TIMESTAMP,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )''')
        
        self._create_demo_data(c)
        # Add optional subscription expiry column to users for subscription tracking
        columns = self.get_table_columns("users", cursor=c)
        if 'subscription_expires_at' not in columns:
            try:
                c.execute("ALTER TABLE users ADD COLUMN subscription_expires_at TIMESTAMP")
            except Exception:
                pass

        # Ensure scenarios table has steps and conditions columns
        columns = self.get_table_columns("scenarios", cursor=c)
        if 'steps' not in columns:
            try:
                c.execute("ALTER TABLE scenarios ADD COLUMN steps TEXT")
            except Exception:
                pass
        if 'conditions' not in columns:
            try:
                c.execute("ALTER TABLE scenarios ADD COLUMN conditions TEXT")
            except Exception:
                pass

        # Manager subscriptions & history
        c.execute('''CREATE TABLE IF NOT EXISTS manager_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            subscription_type TEXT NOT NULL,
            amount REAL NOT NULL,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            status TEXT DEFAULT 'active',
            payment_method TEXT,
            transaction_id TEXT,
            auto_renew INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS subscription_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subscription_type TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            payment_method TEXT,
            transaction_id TEXT,
            status TEXT DEFAULT 'completed',
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )''')

        # Wallets and wallet transactions
        c.execute('''CREATE TABLE IF NOT EXISTS wallets (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            currency TEXT DEFAULT 'VND',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS wallet_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'VND',
            type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            method TEXT,
            reference TEXT,
            notes TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )''')

        # Seed wallets for existing users
        if self.use_postgres:
            c.execute('''INSERT INTO wallets (user_id, balance, currency)
                         SELECT id, 0, 'VND' FROM users
                         ON CONFLICT (user_id) DO NOTHING''')
        else:
            c.execute('''INSERT OR IGNORE INTO wallets (user_id, balance, currency)
                         SELECT id, 0, 'VND' FROM users''')

        # Ensure managers have expiry date set if missing
        if self.use_postgres:
            c.execute('''UPDATE users
                         SET subscription_expires_at = COALESCE(subscription_expires_at, CURRENT_TIMESTAMP + INTERVAL '30 days')
                         WHERE role = 'manager' AND subscription_expires_at IS NULL''')
        else:
            c.execute('''UPDATE users
                         SET subscription_expires_at = COALESCE(subscription_expires_at, datetime('now', '+30 day'))
                         WHERE role = 'manager' AND subscription_expires_at IS NULL''')
        conn.commit()
        conn.close()
    
    def _create_demo_data(self, cursor):
        # Demo users có role rõ ràng
        demo_users = [
            ('admin@fun.com', 'admin123', 'Admin User', None, 'admin'),
            ('manager@fun.com', 'manager123', 'Manager User', None, 'manager'),
            ('user@fun.com', 'user123', 'Regular User', None, 'user')
        ]
        
        for email, password, name, avatar, role in demo_users:
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            if self.use_postgres:
                cursor.execute('''INSERT INTO users 
                            (email, password, name, avatar, role) VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT (email) DO NOTHING''', 
                         (email, hashed_pw, name, avatar, role))
            else:
                cursor.execute('''INSERT OR IGNORE INTO users 
                            (email, password, name, avatar, role) VALUES (?, ?, ?, ?, ?)''', 
                         (email, hashed_pw, name, avatar, role))
            
            # Get the user ID (whether newly inserted or existing)
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            user_row = cursor.fetchone()
            if user_row:
                user_id = user_row[0]
                # Create default workspace if not exists
                cursor.execute('SELECT id FROM workspaces WHERE user_id = ?', (user_id,))
                if not cursor.fetchone():
                    cursor.execute('''INSERT INTO workspaces (user_id, name, type, description) 
                                    VALUES (?, ?, ?, ?)''',
                                 (user_id, f"{name.split()[0]}'s Workspace", 'personal', 'Demo workspace'))
    
    # User methods
    def create_user(self, email, password, name, role="user", first_name=None, last_name=None, manager_id=None):
        conn = self.get_connection()
        c = conn.cursor()
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        try:
            # Check if first_name column exists
            columns = self.get_table_columns("users", cursor=c)
            
            if 'first_name' in columns:
                c.execute('INSERT INTO users (email, password, name, role, first_name, last_name, manager_id) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                         (email, hashed_pw, name, role, first_name, last_name, manager_id))
            else:
                c.execute('INSERT INTO users (email, password, name, role, manager_id) VALUES (?, ?, ?, ?, ?)', 
                         (email, hashed_pw, name, role, manager_id))
            
            user_id = c.lastrowid
            conn.commit()
            conn.close()
            return user_id
        except Exception as e:
            # Catch both sqlite3.IntegrityError and psycopg2.IntegrityError (wrapped or direct)
            conn.close()
            if "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e):
                raise Exception('Email already exists')
            # Check if it is actually an Integrity Error class name
            if "IntegrityError" in type(e).__name__:
                raise Exception('Email already exists')
            raise e
    
    def get_user_by_email(self, email):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('SELECT id, email, password, name, avatar, theme, role FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0],
                'email': user[1],
                'password': user[2],
                'name': user[3],
                'avatar': user[4],
                'theme': user[5],
                'role': user[6]
            }
        return None
    
    def get_user_by_id(self, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('SELECT id, email, name, avatar, theme, role FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        if user:
            return {
                'id': user[0],
                'email': user[1],
                'name': user[2],
                'avatar': user[3],
                'theme': user[4],
                'role': user[5]
            }
        return None

    
    # Workspace methods
    def get_workspaces(self, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('SELECT id, name, type, description FROM workspaces WHERE user_id = ?', (user_id,))
        workspaces = []
        for row in c.fetchall():
            workspaces.append({
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'description': row[3]
            })
        conn.close()
        return workspaces
    
    def create_workspace(self, user_id, name, workspace_type, description=''):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('INSERT INTO workspaces (user_id, name, type, description) VALUES (?, ?, ?, ?)', 
                 (user_id, name, workspace_type, description))
        workspace_id = c.lastrowid
        conn.commit()
        conn.close()
        return workspace_id

    
    # Item methods
    def get_workspace_items(self, workspace_id, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''SELECT i.id, i.title, i.description, i.type, i.status, i.priority, i.created_at
                    FROM items i
                    JOIN workspaces w ON i.workspace_id = w.id
                    WHERE i.workspace_id = ? AND w.user_id = ?
                    ORDER BY i.created_at DESC''', (workspace_id, user_id))
        items = []
        for row in c.fetchall():
            items.append({
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'type': row[3],
                'status': row[4],
                'priority': row[5],
                'created_at': row[6]
            })
        conn.close()
        return items
    
    def create_item(self, workspace_id, user_id, title, description='', item_type='task', status='todo', priority='medium'):
        conn = self.get_connection()
        c = conn.cursor()
        
        # Verify workspace ownership
        c.execute('SELECT id FROM workspaces WHERE id = ? AND user_id = ?', (workspace_id, user_id))
        if not c.fetchone():
            conn.close()
            raise Exception('Workspace not found or access denied')
        
        c.execute('''INSERT INTO items 
                    (workspace_id, title, description, type, status, priority) 
                    VALUES (?, ?, ?, ?, ?, ?)''', 
                  (workspace_id, title, description, item_type, status, priority))
        item_id = c.lastrowid
        conn.commit()
        conn.close()
        return item_id
    
    def update_item(self, item_id, user_id, data):
        conn = self.get_connection()
        c = conn.cursor()
        
        # Verify ownership
        c.execute('''SELECT i.id FROM items i
                    JOIN workspaces w ON i.workspace_id = w.id
                    WHERE i.id = ? AND w.user_id = ?''', (item_id, user_id))
        
        if not c.fetchone():
            conn.close()
            raise Exception('Item not found or access denied')
        
        # Update item
        update_fields = []
        values = []
        
        if 'title' in data:
            update_fields.append('title = ?')
            values.append(data['title'])
        
        if 'description' in data:
            update_fields.append('description = ?')
            values.append(data['description'])
        
        if 'type' in data:
            update_fields.append('type = ?')
            values.append(data['type'])
        
        if 'status' in data:
            update_fields.append('status = ?')
            values.append(data['status'])
        
        if 'priority' in data:
            update_fields.append('priority = ?')
            values.append(data['priority'])
        
        if update_fields:
            values.append(item_id)
            query = f'UPDATE items SET {", ".join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?'
            c.execute(query, values)
        
        conn.commit()
        conn.close()
    
    def delete_item(self, item_id, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''DELETE FROM items 
                    WHERE id = ? AND workspace_id IN 
                    (SELECT id FROM workspaces WHERE user_id = ?)''', 
                  (item_id, user_id))
        conn.commit()
        conn.close()
    
    # Scenario methods
    def get_scenarios(self, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''SELECT s.id, s.name, s.description, s.steps, s.conditions, 
                           s.status, s.created_at, w.name as workspace_name
                    FROM scenarios s
                    JOIN workspaces w ON s.workspace_id = CAST(w.id AS VARCHAR)
                    WHERE w.user_id = ?
                    ORDER BY s.created_at DESC''', (user_id,))
        scenarios = []
        for row in c.fetchall():
            scenarios.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'steps': row[3],
                'conditions': row[4],
                'active': row[5] == 'active',
                'created_at': row[6],
                'workspace_name': row[7],
                'runs': 0  # TODO: implement runs tracking
            })
        conn.close()
        return scenarios
    
    def get_scenario(self, scenario_id, user_id):
        """Fetch a single scenario scoped to the current user.

        We avoid type casting issues by doing two simple queries instead of a join.
        """
        conn = self.get_connection()
        c = conn.cursor()

        # Get the scenario row first
        # DB Schema Inconsistency: scenarios.id is TEXT, but passed as int
        c.execute('''SELECT id, workspace_id, name, description, steps, conditions, status, created_at
                     FROM scenarios WHERE id = ?''', (str(scenario_id),))
        scenario_row = c.fetchone()
        if not scenario_row:
            conn.close()
            return None

        scenario_workspace_id = scenario_row[1]

        # DB Schema Inconsistency: workspace_id in scenarios is TEXT, but id in workspaces is BIGINT
        try:
            target_workspace_id = int(scenario_workspace_id)
        except (ValueError, TypeError):
            target_workspace_id = scenario_workspace_id

        # Verify the workspace belongs to the user
        c.execute('SELECT name FROM workspaces WHERE id = ? AND user_id = ?', (target_workspace_id, user_id))
        workspace_row = c.fetchone()
        if not workspace_row:
            conn.close()
            return None

        workspace_name = workspace_row[0]
        conn.close()

        return {
            'id': scenario_row[0],
            'name': scenario_row[2],
            'description': scenario_row[3],
            'steps': scenario_row[4],
            'conditions': scenario_row[5],
            'active': scenario_row[6] == 'active',
            'created_at': scenario_row[7],
            'workspace_name': workspace_name,
            'runs': 0
        }
    
    def create_scenario(self, user_id, name, description='', active=False, steps=None):
        conn = self.get_connection()
        c = conn.cursor()
        
        # Get user's default workspace
        c.execute('SELECT id FROM workspaces WHERE user_id = ? LIMIT 1', (user_id,))
        workspace = c.fetchone()
        
        if not workspace:
            # Auto-create a default workspace if none exists
            user_name_query = c.execute('SELECT name FROM users WHERE id = ?', (user_id,)).fetchone()
            user_name = user_name_query[0] if user_name_query else "User"
            workspace_name = f"{user_name}'s Workspace"
            
            c.execute('''INSERT INTO workspaces (user_id, name, type, description) 
                        VALUES (?, ?, ?, ?)''',
                     (user_id, workspace_name, 'personal', 'Default personal workspace'))
            workspace_id = c.lastrowid
        else:
            workspace_id = workspace[0]
        
        status = 'active' if active else 'inactive'
        
        c.execute('''INSERT INTO scenarios 
                    (workspace_id, name, description, status, steps) 
                    VALUES (?, ?, ?, ?, ?)''', 
                  (workspace_id, name, description, status, steps))
        
        scenario_id = c.lastrowid
        conn.commit()
        conn.close()
        return scenario_id
    
    def update_scenario(self, scenario_id, user_id, data):
        conn = self.get_connection()
        c = conn.cursor()
        
        # Verify ownership
        c.execute('''SELECT s.id FROM scenarios s
                    JOIN workspaces w ON s.workspace_id = CAST(w.id AS VARCHAR)
                    WHERE s.id = ? AND w.user_id = ?''', (scenario_id, user_id))
        
        if not c.fetchone():
            raise Exception('Scenario not found or access denied')
        
        # Update scenario
        update_fields = []
        values = []
        
        if 'name' in data:
            update_fields.append('name = ?')
            values.append(data['name'])
        
        if 'description' in data:
            update_fields.append('description = ?')
            values.append(data['description'])
        
        if 'active' in data:
            update_fields.append('status = ?')
            values.append('active' if data['active'] else 'inactive')
            
        if 'steps' in data:
            update_fields.append('steps = ?')
            values.append(data['steps'])
            
        if 'conditions' in data:
            update_fields.append('conditions = ?')
            values.append(data['conditions'])
        
        if update_fields:
            values.append(scenario_id)
            query = f'UPDATE scenarios SET {", ".join(update_fields)} WHERE id = ?'
            c.execute(query, values)
        
        conn.commit()
        conn.close()
    
    def delete_scenario(self, scenario_id, user_id):
        conn = self.get_connection()
        c = conn.cursor()
        
        # Verify ownership and delete
        # We check if the scenario belongs to a workspace owned by the user
        c.execute('''DELETE FROM scenarios 
                    WHERE id = ? AND workspace_id IN 
                    (SELECT CAST(id AS VARCHAR) FROM workspaces WHERE user_id = ?)''', 
                  (scenario_id, user_id))
        
        if c.rowcount == 0:
            # Check if scenario exists at all
            c.execute('SELECT id FROM scenarios WHERE id = ?', (scenario_id,))
            if not c.fetchone():
                # Scenario doesn't exist, so technically it's "gone". 
                # But let's raise error to be consistent with "not found"
                pass 
            
            # If scenario exists but wasn't deleted, it means permission denied
            # However, for robustness, if the user has NO workspace, they shouldn't have scenarios.
            # But if they do (orphan scenarios?), we might want to handle that.
            # For now, just keep the exception but make it clearer.
            raise Exception('Scenario not found or access denied')
        
        conn.commit()
        conn.close()
    
    # Permission methods
    def grant_permission(self, user_id, permission_type, granted_by):
        """Grant a permission to a user (Manager/Admin only)"""
        conn = self.get_connection()
        c = conn.cursor()
        try:
            if self.use_postgres:
                c.execute('''INSERT INTO user_permissions 
                        (user_id, permission_type, granted_by, granted_at, revoked) 
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP, 0)
                        ON CONFLICT (user_id, permission_type) DO UPDATE SET 
                        granted_by = excluded.granted_by,
                        granted_at = CURRENT_TIMESTAMP,
                        revoked = 0
                        ''', 
                     (user_id, permission_type, granted_by))
            else:
                c.execute('''INSERT OR REPLACE INTO user_permissions 
                            (user_id, permission_type, granted_by, granted_at, revoked) 
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP, 0)''', 
                        (user_id, permission_type, granted_by))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise Exception(f'Failed to grant permission: {str(e)}')
        finally:
            conn.close()
    
    def revoke_permission(self, user_id, permission_type):
        """Revoke a permission from a user"""
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute('''UPDATE user_permissions SET revoked = 1 
                        WHERE user_id = ? AND permission_type = ?''', 
                     (user_id, permission_type))
            conn.commit()
            return c.rowcount > 0
        finally:
            conn.close()
    
    def get_user_permissions(self, user_id):
        """Get all active permissions for a user"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''SELECT permission_type, granted_at, granted_by 
                    FROM user_permissions 
                    WHERE user_id = ? AND revoked = 0''', (user_id,))
        permissions = []
        for row in c.fetchall():
            permissions.append({
                'permission_type': row[0],
                'granted_at': row[1],
                'granted_by': row[2]
            })
        conn.close()
        return permissions
    
    def has_permission(self, user_id, permission_type):
        """Check if user has a specific permission"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''SELECT COUNT(*) FROM user_permissions 
                    WHERE user_id = ? AND permission_type = ? AND revoked = 0''', 
                 (user_id, permission_type))
        count = c.fetchone()[0]
        conn.close()
        return count > 0
    
    def get_all_users_with_permissions(self):
        """Get all users with their permissions (for Manager/Admin view)"""
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''SELECT u.id, u.name, u.email, u.role, 
                           GROUP_CONCAT(CASE WHEN p.revoked = 0 THEN p.permission_type END) as permissions
                    FROM users u
                    LEFT JOIN user_permissions p ON u.id = p.user_id
                    GROUP BY u.id
                    ORDER BY u.name''')
        users = []
        for row in c.fetchall():
            users.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'role': row[3],
                'permissions': row[4].split(',') if row[4] else []
            })
        conn.close()
        return users

    # Customer methods
    def get_customers(self, created_by=None):
        conn = self.get_connection()
        c = conn.cursor()
        query = 'SELECT id, code, name, phone, email, address, notes, created_at FROM customers'
        params = []
        if created_by:
            query += ' WHERE created_by = ?'
            params.append(created_by)
        query += ' ORDER BY created_at DESC'
        
        c.execute(query, params)
        customers = []
        for row in c.fetchall():
            customers.append({
                'id': row[0],
                'code': row[1],
                'name': row[2],
                'phone': row[3],
                'email': row[4],
                'address': row[5],
                'notes': row[6],
                'created_at': row[7]
            })
        conn.close()
        return customers

    def create_customer(self, code, name, phone, email, address, notes, created_by):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO customers 
                        (code, name, phone, email, address, notes, created_by) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                     (code, name, phone, email, address, notes, created_by))
            customer_id = c.lastrowid
            conn.commit()
            conn.close()
            return customer_id
        except sqlite3.IntegrityError:
            conn.close()
            raise Exception('Customer code already exists')

    # Product methods
    def get_products(self, created_by=None):
        conn = self.get_connection()
        c = conn.cursor()
        query = 'SELECT id, code, name, category, unit, price, stock_quantity, description, created_at FROM products'
        params = []
        if created_by:
            query += ' WHERE created_by = ?'
            params.append(created_by)
        query += ' ORDER BY created_at DESC'
        
        c.execute(query, params)
        products = []
        for row in c.fetchall():
            products.append({
                'id': row[0],
                'code': row[1],
                'name': row[2],
                'category': row[3],
                'unit': row[4],
                'price': row[5],
                'stock_quantity': row[6],
                'description': row[7],
                'created_at': row[8]
            })
        conn.close()
        return products

    def create_product(self, code, name, category, unit, price, stock_quantity, description, created_by):
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO products 
                        (code, name, category, unit, price, stock_quantity, description, created_by) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                     (code, name, category, unit, price, stock_quantity, description, created_by))
            product_id = c.lastrowid
            conn.commit()
            conn.close()
            return product_id
        except sqlite3.IntegrityError:
            conn.close()
            raise Exception('Product code already exists')

    def log_activity(self, user_id, action, details=None, ip_address=None):
        """Log user activity"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            c.execute('INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
                     (user_id, action, details, ip_address))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error logging activity: {e}")
            return False

    def get_recent_activities(self, limit=10):
        """Get recent system activities"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # Check if google_token column exists once
        # c.execute("PRAGMA table_info(users)")
        # columns = [col[1] for col in c.fetchall()]
        columns = self.get_table_columns("users", cursor=c)
        has_google_token = 'google_token' in columns
        
        # Simplified and more robust query
        query = '''
            SELECT a.id, a.action, a.details, a.created_at, u.name, u.email,
                   {}
            FROM activity_logs a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
            LIMIT ?
        '''.format('u.google_token' if has_google_token else 'NULL as google_token')

        c.execute(query, (limit,))
            
        activities = []
        for row in c.fetchall():
            # Handle datetime objects (Postgres) or strings (SQLite)
            created_at = row[3]
            if hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            
            activities.append({
                'id': row[0],
                'action': row[1],
                'details': row[2],
                'created_at': created_at,
                'user_name': row[4] or 'System',
                'user_email': row[5],
                'is_google_user': bool(row[6]) if has_google_token else False
            })
        conn.close()
        return activities