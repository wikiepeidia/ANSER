"""Activity log repository — reads and writes activity_logs table."""
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
            return [
                {'id': r['id'], 'user_id': r['user_id'], 'action': r['action'],
                 'details': r['details'], 'ip_address': r['ip_address'],
                 'created_at': r['created_at']}
                for r in c.fetchall()
            ]
        except Exception:
            return []

    def log_activity(self, user_id, action, details=None, ip_address=None):
        c = self.conn.cursor()
        c.execute(
            'INSERT INTO activity_logs (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)',
            (user_id, action, details, ip_address),
        )
        self.conn.commit()
