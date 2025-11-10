#!/usr/bin/env python3
"""
Simple database creation script
"""

import sqlite3
import hashlib
import os

def create_fresh_database():
    # Remove old database if exists
    db_path = 'fun_work_hub.db'  # Use correct database name
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed old database: {db_path}")
    
    # Create new database
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("Creating users table with new schema...")
    
    # Users table with role and phone
    c.execute('''CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT NOT NULL,
        avatar TEXT,
        phone TEXT,
        role TEXT DEFAULT 'user',
        theme TEXT DEFAULT 'dark',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Create workspaces table
    c.execute('''CREATE TABLE workspaces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        type TEXT DEFAULT 'personal',
        description TEXT,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    # Insert admin user
    print("Creating admin user...")
    admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
    c.execute('''INSERT INTO users (name, email, password, role, phone) 
                VALUES (?, ?, ?, ?, ?)''',
             ('Admin User', 'admin@admin.com', admin_pass, 'admin', '+84123456789'))
    
    # Insert test user
    user_pass = hashlib.sha256('user123'.encode()).hexdigest()  
    c.execute('''INSERT INTO users (name, email, password, role, phone) 
                VALUES (?, ?, ?, ?, ?)''',
             ('Test User', 'user@test.com', user_pass, 'user', '+84987654321'))
    
    conn.commit()
    conn.close()
    
    print("✓ Database created successfully!")
    print("✓ Admin account: admin@admin.com / admin123")
    print("✓ Test account: user@test.com / user123")

if __name__ == '__main__':
    create_fresh_database()