import sqlite3
import re
from datetime import datetime
from .config import Config
import bcrypt

# Compatibility shim
try:
    from app.db import SessionLocal, Base
except Exception:
    SessionLocal = None
    Base = None

class PGShimCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None
        self.rowcount = -1

    def execute(self, query, params=None):
        has_params = params is not None and len(params) > 0
        query = query.replace('?', '%s')
        is_insert = query.strip().upper().startswith('INSERT')
        try:
            if is_insert and 'RETURNING' not in query.upper():
                query += " RETURNING id"
                self._cursor.execute(query, params) if has_params else self._cursor.execute(query)
                row = self._cursor.fetchone()
                if row: self.lastrowid = row[0]
            else:
                self._cursor.execute(query, params) if has_params else self._cursor.execute(query)
                self.lastrowid = None
            self.rowcount = self._cursor.rowcount
            return self
        except Exception as e:
            if is_insert and 'RETURNING id' in query:
                try:
                    if hasattr(self._cursor, 'connection'): self._cursor.connection.rollback()
                except: pass
                clean_query = query.replace(" RETURNING id", "")
                self._cursor.execute(clean_query, params) if has_params else self._cursor.execute(clean_query)
                self.lastrowid = None
                return self
            raise e

    def executemany(self, query, params_seq):
        query = query.replace('?', '%s')
        self._cursor.executemany(query, params_seq)
        return self

    def fetchone(self): return self._cursor.fetchone()
    def fetchall(self): return self._cursor.fetchall()
    def fetchmany(self, size=None): return self._cursor.fetchmany(size)
    def close(self): self._cursor.close()
    def __getattr__(self, name): return getattr(self._cursor, name)

class PGShimConnection:
    def __init__(self, conn):
        self._conn = conn
        self.row_factory = None
    def cursor(self): return PGShimCursor(self._conn.cursor())
    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self): self._conn.close()

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.use_postgres = getattr(Config, 'USE_POSTGRES', False)
        # Only init if not Postgres to avoid schema conflicts, or use migration scripts
        if not self.use_postgres:
            self.init_database()

    def get_table_columns(self, table_name, cursor=None):
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
                try: cursor.close()
                except: pass
                try: conn.close()
                except: pass

    def get_connection(self):
        if self.use_postgres:
            import psycopg2
            conn = psycopg2.connect(Config.POSTGRES_URL)
            return PGShimConnection(conn)
        else:
            return sqlite3.connect(self.db_path, timeout=30.0)
    
    def init_database(self):
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
            # Check columns to valid safely or just select *? 
            # Safer to select specific columns, assuming schema is up to date (we ran fix scripts)
            c.execute('SELECT id, email, name, avatar, theme, role, first_name, last_name, google_token FROM users WHERE id = ?', (user_id,))
            user = c.fetchone()
        except Exception:
            # Fallback for old schema if columns missing (though we should have them)
            c.execute('SELECT id, email, name, avatar, theme, role FROM users WHERE id = ?', (user_id,))
            user = c.fetchone()
            if user: # Pad with None
                user = user + (None, None, None)

        conn.close()
        if user:
            return {
                'id': user[0], 
                'email': user[1], 
                'name': user[2], 
                'avatar': user[3], 
                'theme': user[4], 
                'role': user[5],
                'first_name': user[6],
                'last_name': user[7],
                'google_token': user[8]
            }
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
        c.execute('SELECT * FROM workspaces WHERE user_id = ? ORDER BY created_at', (user_id,))
        workspaces = c.fetchall()
        conn.close()
        return workspaces

    def get_all_users_with_permissions(self):
        conn = self.get_connection()
        c = conn.cursor()
        c.execute('''SELECT u.id, u.name, u.email, u.role, '' as permissions FROM users u''')
        users = []
        for row in c.fetchall():
            users.append({'id': row[0], 'name': row[1], 'email': row[2], 'role': row[3], 'permissions': []})
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
                {'id': r[0], 'user_id': r[1], 'action': r[2],
                 'details': r[3], 'ip_address': r[4], 'created_at': r[5]}
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
        except: return False

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
            print(f"⚠️ Memory Save Error: {e}")
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
                role_name = "User" if r[0] == 'user' else "AI"
                history.append(f"{role_name}: {r[1]}")
            
            return "\n".join(history)
        except Exception as e:
            print(f"⚠️ Memory Fetch Error: {e}")
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
                sid = row[0]
            else:
                if self.use_postgres:
                    c.execute("INSERT INTO chat_sessions (user_id, workspace_id, title) VALUES (%s, %s, 'New Chat') RETURNING id", (user_id, workspace_id))
                    sid = c.fetchone()[0]
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
            print(f"❌ DB Attachment Error: {e}")
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
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'updated_at': row[3],
                    'data': row[4],
                    'steps': row[4]
                })
            return scenarios
        except Exception as e:
            print(f"Error fetching scenarios: {e}")
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
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'updated_at': row[3],
                    'data': row[4],
                    'steps': row[4],
                    'user_id': row[5]
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

