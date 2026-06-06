#!/usr/bin/env python3
"""
NeonDB Fix — Add password_version column to users table if missing.

This script:
1. Checks if password_version column exists
2. Adds it if missing (with DEFAULT 0)
3. Marks all existing passwords as legacy (version 0)

Usage:
    python debug/fix_neon_password_version.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
import psycopg2
from psycopg2.extras import DictCursor

def fix_password_version():
    """Add password_version column to users table if missing."""
    try:
        print("=" * 70)
        print("NeonDB PASSWORD_VERSION FIX")
        print("=" * 70)
        print(f"🔧 Connecting to: {Config.POSTGRES_URL[:50]}...\n")
        
        conn = psycopg2.connect(Config.POSTGRES_URL)
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # ─────────────────────────────────────────────────────────────────
        # 1. Check if column exists
        # ─────────────────────────────────────────────────────────────────
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'password_version'
        """)
        
        column_exists = cursor.fetchone() is not None
        
        if column_exists:
            print("✅ password_version column already exists — no action needed")
            cursor.close()
            conn.close()
            return True
        
        # ─────────────────────────────────────────────────────────────────
        # 2. Add the column
        # ─────────────────────────────────────────────────────────────────
        print("⏳ Adding password_version column to users table...")
        try:
            cursor.execute("""
                ALTER TABLE users
                ADD COLUMN password_version INTEGER DEFAULT 0
            """)
            conn.commit()
            print("✅ Column added successfully")
        except psycopg2.Error as e:
            print(f"❌ Failed to add column: {e}")
            conn.rollback()
            return False
        
        # ─────────────────────────────────────────────────────────────────
        # 3. Verify and report
        # ─────────────────────────────────────────────────────────────────
        cursor.execute("""
            SELECT COUNT(*) as user_count
            FROM users
        """)
        user_count = cursor.fetchone()['user_count']
        
        print(f"✅ {user_count} existing users marked as legacy (password_version = 0)")
        print("   → On next login, passwords will be automatically rehashed with bcrypt")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("✅ FIX COMPLETE")
        print("=" * 70)
        print("Next steps:")
        print("  1. Restart the application: python app.py")
        print("  2. Test login with any user account")
        print("  3. Password should be auto-rehashed on first login")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    success = fix_password_version()
    sys.exit(0 if success else 1)
