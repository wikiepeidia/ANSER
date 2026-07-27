"""Read-only connector to ANSER's shared `users` table.

This app never writes to it and never verifies passwords — signin only
happens on the ANSER app (port 5000). We only need to resolve a user id
(decoded from the shared session cookie) into a display-able user.
"""
import sqlite3

from core.config import Config


def _get_conn():
    if Config.AUTH_USE_POSTGRES:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(Config.AUTH_POSTGRES_URL)
        return conn, '%s'
    conn = sqlite3.connect(Config.AUTH_DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn, '?'


def count_managers():
    """Count of role='manager' accounts in the shared users table — same
    "how many shop owners signed up" proxy metric Retail's own
    /api/internal/platform-stats uses, for Gateway's cross-app admin page."""
    conn, ph = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE role = 'manager'")
        return cur.fetchone()[0] or 0
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn, ph = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            f'SELECT id, email, first_name, last_name, role, avatar FROM users WHERE id = {ph}',
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        if Config.AUTH_USE_POSTGRES:
            cols = [d.name for d in cur.description]
            row = dict(zip(cols, row))
        else:
            row = dict(row)
        return row
    finally:
        conn.close()
