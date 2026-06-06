#!/usr/bin/env python3
"""Quick check of user passwords in NeonDB."""
import sys
sys.path.insert(0, '.')
from core.config import Config
import psycopg2
from psycopg2.extras import DictCursor

conn = psycopg2.connect(Config.POSTGRES_URL)
cursor = conn.cursor(cursor_factory=DictCursor)

cursor.execute("""
    SELECT id, email, password, password_version 
    FROM users 
    ORDER BY id
    LIMIT 10
""")

users = cursor.fetchall()
print(f"\n🔍 Found {len(users)} users:\n")
for user in users:
    pwd = user['password'][:35] if user['password'] else 'NULL'
    pv = user['password_version']
    
    # Detect hash type
    hash_type = "UNKNOWN"
    if pwd.startswith('$2b$') or pwd.startswith('$2a$') or pwd.startswith('$2y$'):
        hash_type = "BCRYPT (modern)"
    elif len(pwd) == 64 and all(c in '0123456789abcdef' for c in pwd):
        hash_type = "SHA256 (legacy)"
    
    print(f"  {user['id']:3} | {user['email']:25} | {hash_type:18} | Ver:{pv}")

cursor.close()
conn.close()
print()
