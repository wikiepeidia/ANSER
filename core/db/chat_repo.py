"""AI chat repository — ai_chat_history, chat_sessions, chat_attachments."""
from core.logger import get_logger

logger = get_logger(__name__)


def _is_postgres(conn) -> bool:
    return hasattr(conn, '_pool')


class ChatRepo:
    def __init__(self, conn):
        self.conn = conn

    def add_ai_message(self, user_id, role, content):
        c = self.conn.cursor()
        try:
            c.execute(
                'INSERT INTO ai_chat_history (user_id, role, content, created_at)'
                ' VALUES (?, ?, ?, CURRENT_TIMESTAMP)',
                (user_id, role, content),
            )
            self.conn.commit()
        except Exception as e:
            logger.error("Memory save error for user %s: %s", user_id, e, exc_info=True)

    def get_ai_history(self, user_id, limit=6):
        c = self.conn.cursor()
        try:
            c.execute(
                'SELECT role, content FROM ai_chat_history'
                ' WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
                (user_id, limit),
            )
            rows = c.fetchall()
            history = []
            for r in reversed(rows):
                role_name = "User" if r['role'] == 'user' else "AI"
                history.append(f"{role_name}: {r['content']}")
            return "\n".join(history)
        except Exception as e:
            logger.error("Memory fetch error for user %s: %s", user_id, e, exc_info=True)
            return ""

    def save_attachment(self, user_id, workspace_id, filename, filetype, analysis):
        c = self.conn.cursor()
        try:
            c.execute(
                "SELECT id FROM chat_sessions WHERE user_id = ? ORDER BY last_active DESC LIMIT 1",
                (user_id,),
            )
            row = c.fetchone()
            if row:
                sid = row['id']
            else:
                c.execute(
                    "INSERT INTO chat_sessions (user_id, workspace_id, title) VALUES (?, ?, 'New Chat')",
                    (user_id, workspace_id),
                )
                sid = c.lastrowid

            c.execute(
                "INSERT INTO chat_attachments"
                " (session_id, file_name, file_type, analysis_summary) VALUES (?, ?, ?, ?)",
                (sid, filename, filetype, analysis),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(
                "DB attachment save error for user %s, file %s: %s",
                user_id, filename, e, exc_info=True,
            )
