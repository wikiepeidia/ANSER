"""Activity log repository — reads and writes activity_logs table."""
from datetime import datetime, timezone
from core.logger import get_logger

logger = get_logger(__name__)


class ActivityRepo:
    def __init__(self, conn):
        self.conn = conn

    def get_recent_activities(self, limit=20):
        c = self.conn.cursor()
        try:
            c.execute(
                'SELECT id, user_id, action, details, ip_address, created_at '
                'FROM activity_logs ORDER BY created_at DESC LIMIT ?', (limit,)
            )
            rows = []
            for r in c.fetchall():
                ts = r['created_at']
                # Normalise to ISO 8601 string so JS new Date() parses reliably
                if isinstance(ts, datetime):
                    ts = ts.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                elif isinstance(ts, str) and ts and 'T' not in ts:
                    ts = ts.replace(' ', 'T') + 'Z'
                rows.append({
                    'id': r['id'], 'user_id': r['user_id'], 'action': r['action'],
                    'details': r['details'], 'ip_address': r['ip_address'],
                    'created_at': ts,
                })
            return rows
        except Exception:
            return []

    def log_activity(self, user_id, action, details=None, ip_address=None):
        c = self.conn.cursor()
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        c.execute(
            'INSERT INTO activity_logs (user_id, action, details, ip_address, created_at)'
            ' VALUES (?, ?, ?, ?, ?)',
            (user_id, action, details, ip_address, now),
        )
        self.conn.commit()
