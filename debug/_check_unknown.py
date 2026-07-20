import sys
sys.path.insert(0, '.')
from core.config import Config
import psycopg2
from psycopg2.extras import DictCursor
conn = psycopg2.connect(Config.POSTGRES_URL)
cur = conn.cursor(cursor_factory=DictCursor)
cur.execute("SELECT id, email, SUBSTRING(password, 1, 12) as pfx, LENGTH(password) as plen, password_version FROM users WHERE password_version=0 ORDER BY id LIMIT 8")
for u in cur.fetchall():
    print(dict(u))
