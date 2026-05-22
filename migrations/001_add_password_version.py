#!/usr/bin/env python3
"""
Migration: Add password_version column to users table.

This migration marks all existing passwords as version 0 (legacy sha256).
On next login, they will be automatically rehashed with bcrypt.

Usage:
    python migrations/001_add_password_version.py
"""
import sqlite3
import psycopg2
from pathlib import Path
import sys

def migrate_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in c.fetchall()]
        if 'password_version' in columns:
            print("✓ password_version column already exists")
            return
        print("Adding password_version column to SQLite users table...")
        c.execute("ALTER TABLE users ADD COLUMN password_version INTEGER DEFAULT 0")
        conn.commit()
        print("✓ SQLite migration complete")
    except Exception as e:
        print(f"✗ SQLite migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

def migrate_postgres(pg_url):
    try:
        conn = psycopg2.connect(pg_url)
        c = conn.cursor()
        try:
            c.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'password_version'
            """)
            if c.fetchone():
                print("✓ password_version column already exists")
                return
            print("Adding password_version column to PostgreSQL users table...")
            c.execute("ALTER TABLE users ADD COLUMN password_version INTEGER DEFAULT 0")
            conn.commit()
            print("✓ PostgreSQL migration complete")
        except Exception as e:
            print(f"✗ PostgreSQL migration failed: {e}")
            conn.rollback()
        finally:
            c.close()
            conn.close()
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")

if __name__ == '__main__':
    from core.config import Config
    if Config.USE_POSTGRES:
        migrate_postgres(Config.POSTGRES_URL)
    else:
        migrate_sqlite(Config.DATABASE_PATH)
    print("\n💡 Migration complete. Old passwords will be rehashed on next login.")
