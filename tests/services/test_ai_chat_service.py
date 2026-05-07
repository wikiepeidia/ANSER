"""Unit tests for AI chat service delegation behavior."""

import pytest

import core.services.ai_chat_service as ai_chat_service
from core.services.service_errors import ServiceValidationError


class _HistoryCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def execute(self, query, params):
        self.executed.append((query, params))

    def fetchall(self):
        return self.rows


class _HistoryConn:
    def __init__(self, rows):
        self._cursor = _HistoryCursor(rows)
        self.commits = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1


@pytest.mark.parametrize("message", ["xin chào", "hello", "hi", "chào"])
def test_resolve_greeting_reply_matrix(message):
    reply = ai_chat_service.resolve_greeting_reply(message)
    assert isinstance(reply, str)
    assert "trợ lý ảo" in reply


def test_empty_message_rejected():
    with pytest.raises(ServiceValidationError):
        ai_chat_service.normalize_message("   ")


def test_fetch_chat_history_formats_rows_for_http_json():
    conn = _HistoryConn(rows=[("user", "Hi"), ("assistant", "Hello")])

    history = ai_chat_service.fetch_chat_history(conn, user_id=9, limit=50)

    assert history == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]
    assert conn._cursor.executed
