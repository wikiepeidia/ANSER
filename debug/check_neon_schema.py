#!/usr/bin/env python3
"""
Schema checker for NeonDB — diagnose missing columns across all tables.
Especially validates: password_version in users table.

Usage:
    python debug/check_neon_schema.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import Config
import psycopg2
from psycopg2.extras import DictCursor

def check_neon_schema():
    """Connect to NeonDB and inspect full schema."""
    try:
        print("=" * 70)
        print("NeonDB SCHEMA DIAGNOSTIC")
        print("=" * 70)
        print(f"🔍 Connecting to: {Config.POSTGRES_URL[:50]}...\n")
        
        conn = psycopg2.connect(Config.POSTGRES_URL)
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # ─────────────────────────────────────────────────────────────────
        # 1. List all tables
        # ─────────────────────────────────────────────────────────────────
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row['table_name'] for row in cursor.fetchall()]
        print(f"📋 Found {len(tables)} tables:")
        for table in tables:
            print(f"   - {table}")
        print()
        
        # ─────────────────────────────────────────────────────────────────
        # 2. CRITICAL: Check users table for password_version
        # ─────────────────────────────────────────────────────────────────
        print("🔐 CRITICAL CHECK: users table columns")
        print("-" * 70)
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        users_columns = cursor.fetchall()
        
        if not users_columns:
            print("❌ ERROR: users table does not exist!")
            return False
        
        password_version_found = False
        for col in users_columns:
            col_name = col['column_name']
            col_type = col['data_type']
            nullable = col['is_nullable']
            default = col['column_default']
            
            marker = ""
            if col_name == 'password_version':
                marker = " ✅ [REQUIRED]"
                password_version_found = True
            elif col_name == 'password':
                marker = " ✅ [REQUIRED]"
            elif col_name == 'email':
                marker = " ✅ [REQUIRED]"
            
            print(f"   {col_name:20} {col_type:15} NULL={nullable:5} DEFAULT={default}{marker}")
        
        print()
        if not password_version_found:
            print("❌ MISSING: password_version column NOT FOUND in users table")
            print("   → This is the ROOT CAUSE of auth failures")
            return False
        else:
            print("✅ password_version column EXISTS")
        
        print()
        
        # ─────────────────────────────────────────────────────────────────
        # 3. Check other critical tables
        # ─────────────────────────────────────────────────────────────────
        print("📊 OTHER CRITICAL TABLES:")
        print("-" * 70)
        
        critical_tables = ['workspaces', 'customers', 'products', 'workflows', 'activities']
        for table in critical_tables:
            if table in tables:
                cursor.execute(f"""
                    SELECT COUNT(*) as col_count
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                """)
                col_count = cursor.fetchone()['col_count']
                print(f"   {table:20} ✅ ({col_count} columns)")
            else:
                print(f"   {table:20} ⚠️  NOT FOUND")
        
        print()
        
        # ─────────────────────────────────────────────────────────────────
        # 4. Summary
        # ─────────────────────────────────────────────────────────────────
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        if password_version_found:
            print("✅ NeonDB schema is VALID — password_version column exists")
            print("   → If auth is still failing, check:")
            print("      1. Application is using updated code")
            print("      2. App was restarted after code changes")
            return True
        else:
            print("❌ NeonDB schema is INVALID — password_version column MISSING")
            print("   → Run: python debug/fix_neon_password_version.py")
            return False
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    success = check_neon_schema()
    sys.exit(0 if success else 1)
