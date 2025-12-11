#!/usr/bin/env python3
"""
Complete Database Setup Script
Merges all previous migration and creation scripts into one.
Creates the database schema and populates initial data.
"""

import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

# Configuration
DB_PATH = os.environ.get('DATABASE_PATH', 'group_project_ai_ml.db')

def setup_database():
    print(f"🔧 Setting up database: {DB_PATH}")
    
    # Remove old database if exists to ensure fresh start
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"✓ Removed old database: {DB_PATH}")
        except PermissionError:
            print(f"❌ Error: Cannot remove {DB_PATH}. It might be in use.")
            return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ==========================================
    # 1. Create Tables
    # ==========================================

    print("Creating tables...")

    # Users Table
    # Merges fields from create_database.py, migrate_database.py, migrate_user_columns.py, migrate_subscriptions.py
    c.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        avatar TEXT,
        phone TEXT,
        role TEXT DEFAULT 'user',
        theme TEXT DEFAULT 'dark',
        google_token TEXT,
        subscription_expires_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Workspaces Table
    c.execute('''CREATE TABLE workspaces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        type TEXT DEFAULT 'personal',
        description TEXT,
        settings TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    # Items Table (Tasks/Items)
    c.execute('''CREATE TABLE items (
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

    # Scenarios Table
    c.execute('''CREATE TABLE scenarios (
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

    # Channels Table
    c.execute('''CREATE TABLE channels (
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

    # User Permissions Table
    c.execute('''CREATE TABLE user_permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        permission_type TEXT NOT NULL,
        resource_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')

    # Manager Subscriptions Table
    c.execute('''CREATE TABLE manager_subscriptions (
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

    # Subscription History Table
    c.execute('''CREATE TABLE subscription_history (
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

    print("✓ All tables created successfully.")

    # ==========================================
    # 2. Insert Initial Data
    # ==========================================

    print("Inserting initial data...")

    # Helper to hash password
    def hash_pw(password):
        return hashlib.sha256(password.encode()).hexdigest()

    # 1. Admin User
    admin_pass = hash_pw('admin123')
    c.execute('''INSERT INTO users (name, first_name, last_name, email, password, role, phone) 
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
             ('Admin User', 'Admin', 'User', 'admin@admin.com', admin_pass, 'admin', '+84123456789'))
    admin_id = c.lastrowid
    
    # Admin Workspace
    c.execute('''INSERT INTO workspaces (user_id, name, type, description) 
                VALUES (?, ?, ?, ?)''',
             (admin_id, "Admin's Workspace", 'personal', 'System Administration'))

    # 2. Test User
    user_pass = hash_pw('user123')
    c.execute('''INSERT INTO users (name, first_name, last_name, email, password, role, phone) 
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
             ('Test User', 'Test', 'User', 'user@test.com', user_pass, 'user', '+84987654321'))
    user_id = c.lastrowid

    # Test User Workspace
    c.execute('''INSERT INTO workspaces (user_id, name, type, description) 
                VALUES (?, ?, ?, ?)''',
             (user_id, "Test User's Workspace", 'personal', 'My Personal Workspace'))

    # 3. Demo User
    demo_pass = hash_pw('1234')
    c.execute('''INSERT INTO users (name, first_name, last_name, email, password, role) 
                VALUES (?, ?, ?, ?, ?, ?)''',
             ('Demo User', 'Demo', 'User', 'user@demo.com', demo_pass, 'user'))
    demo_id = c.lastrowid

    # Demo User Workspace
    c.execute('''INSERT INTO workspaces (user_id, name, type, description) 
                VALUES (?, ?, ?, ?)''',
             (demo_id, "Demo Workspace", 'personal', 'Demo Area'))

    # 4. Manager User (for subscription testing)
    manager_pass = hash_pw('manager123')
    c.execute('''INSERT INTO users (name, first_name, last_name, email, password, role, phone) 
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
             ('Manager User', 'Manager', 'User', 'manager@test.com', manager_pass, 'manager', '+84999999999'))
    manager_id = c.lastrowid

    # Manager Subscription (Trial)
    start_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT INTO manager_subscriptions 
                (user_id, subscription_type, amount, start_date, end_date, status)
                VALUES (?, ?, ?, ?, ?, ?)''',
                (manager_id, 'trial', 0, start_date, end_date, 'active'))
    
    # Update manager expiry in users table
    c.execute("UPDATE users SET subscription_expires_at = ? WHERE id = ?", (end_date, manager_id))

    conn.commit()
    conn.close()

    print("\n✅ Database setup completed successfully!")
    print("----------------------------------------")
    print("Created Accounts:")
    print("1. Admin:   admin@admin.com / admin123")
    print("2. User:    user@test.com   / user123")
    print("3. Demo:    user@demo.com   / 1234")
    print("4. Manager: manager@test.com / manager123")
    print("----------------------------------------")

if __name__ == '__main__':
    setup_database()
