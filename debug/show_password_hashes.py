#!/usr/bin/env python3
"""Show actual password values in database."""
import sys
sys.path.insert(0, '.')
from core.config import Config
import psycopg2
from psycopg2.extras import DictCursor

conn = psycopg2.connect(Config.POSTGRES_URL)
cursor = conn.cursor(cursor_factory=DictCursor)

cursor.execute("""
    SELECT email, password, length(password) as pwd_len, password_version 
    FROM users 
    LIMIT 5
""")

for user in cursor.fetchall():
    print(f"\n📧 Email: {user['email']}")
    print(f"   Length: {user['pwd_len']} chars")
    print(f"   Version: {user['password_version']}")
    pwd = user['password']
    if pwd:
        print(f"   First 60 chars: {pwd[:60]}")
        if len(pwd) > 60:
            print(f"   Last 20 chars: ...{pwd[-20:]}")
    else:
        print(f"   Password: NULL or empty!")

cursor.close()
conn.close()
