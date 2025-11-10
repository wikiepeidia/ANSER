import sqlite3
import hashlib
from datetime import datetime
from .config import Config

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        conn = self.get_connection()
        c = conn.cursor()
        
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

        # Nếu bảng cũ chưa có cột role thì thêm
        c.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in c.fetchall()]
        if 'role' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        
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
        
        self._create_demo_data(c)
        conn.commit()
        conn.close()
    
    def _create_demo_data(self, cursor):
        # Demo users có role rõ ràng
        demo_users = [
            ('admin@fun.com', 'admin123', 'Admin User', None, 'admin'),
            ('user@fun.com', 'user123', 'Regular User', None, 'user')
        ]
        
        for email, password, name, avatar, role in demo_users:
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('''INSERT OR IGNORE INTO users 
                            (email, password, name, avatar, role) VALUES (?, ?, ?, ?, ?)''', 
                         (email, hashed_pw, name, avatar, role))
    
    # User methods
    def create_user(self, email, password, name, role="user"):
        conn = self.get_connection()
        c = conn.cursor()
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        try:
            c.execute('INSERT INTO users (email, password, name, role) VALUES (?, ?, ?, ?)', 
                     (email, hashed_pw, name, role))
            user_id = c.lastrowid
            conn.commit()
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            conn.close()
            raise Exception('Email already exists')
    
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
                    JOIN workspaces w ON s.workspace_id = w.id
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
    
    def create_scenario(self, user_id, name, description='', active=False):
        conn = self.get_connection()
        c = conn.cursor()
        
        # Get user's default workspace
        c.execute('SELECT id FROM workspaces WHERE user_id = ? LIMIT 1', (user_id,))
        workspace = c.fetchone()
        if not workspace:
            raise Exception('No workspace found for user')
        
        workspace_id = workspace[0]
        status = 'active' if active else 'inactive'
        
        c.execute('''INSERT INTO scenarios 
                    (workspace_id, name, description, status) 
                    VALUES (?, ?, ?, ?)''', 
                  (workspace_id, name, description, status))
        
        scenario_id = c.lastrowid
        conn.commit()
        conn.close()
        return scenario_id
    
    def update_scenario(self, scenario_id, user_id, data):
        conn = self.get_connection()
        c = conn.cursor()
        
        # Verify ownership
        c.execute('''SELECT s.id FROM scenarios s
                    JOIN workspaces w ON s.workspace_id = w.id
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
        c.execute('''DELETE FROM scenarios 
                    WHERE id = ? AND workspace_id IN 
                    (SELECT id FROM workspaces WHERE user_id = ?)''', 
                  (scenario_id, user_id))
        
        if c.rowcount == 0:
            raise Exception('Scenario not found or access denied')
        
        conn.commit()
        conn.close()