#!/usr/bin/env python3
"""
Database Migration Script
Adds role and phone columns to existing database
"""

import sqlite3
import os

def migrate_database():
    db_path = 'workspace_management.db'
    
    if not os.path.exists(db_path):
        print("Database doesn't exist. No migration needed.")
        return
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Check if columns already exist
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        
        # Add role column if it doesn't exist
        if 'role' not in columns:
            print("Adding 'role' column to users table...")
            c.execute('ALTER TABLE users ADD COLUMN role TEXT DEFAULT "user"')
            print("✓ Role column added")
        else:
            print("✓ Role column already exists")
            
        # Add phone column if it doesn't exist  
        if 'phone' not in columns:
            print("Adding 'phone' column to users table...")
            c.execute('ALTER TABLE users ADD COLUMN phone TEXT')
            print("✓ Phone column added")
        else:
            print("✓ Phone column already exists")
        
        # Update existing admin user if exists
        c.execute("SELECT id FROM users WHERE email = 'admin@admin.com'")
        admin_user = c.fetchone()
        
        if admin_user:
            c.execute("UPDATE users SET role = 'admin' WHERE email = 'admin@admin.com'")
            print("✓ Updated existing admin user role")
        else:
            # Create admin user
            import hashlib
            admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
            c.execute('''INSERT INTO users (name, email, password, role, phone) 
                        VALUES (?, ?, ?, ?, ?)''',
                     ('Admin User', 'admin@admin.com', admin_pass, 'admin', '+84123456789'))
            print("✓ Created admin user (email: admin@admin.com, password: admin123)")
            
        conn.commit()
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()