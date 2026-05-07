"""Shared fixtures for service-layer unit tests."""

import pytest


class _CursorStub:
    def __init__(self):
        self.lastrowid = 1

    def execute(self, query, params=None):
        return None

    def fetchall(self):
        return []

    def fetchone(self):
        return (5,)


class _DBStub:
    def __init__(self):
        self._cursor = _CursorStub()

    def cursor(self):
        return self._cursor

    def commit(self):
        return None

    def rollback(self):
        return None


@pytest.fixture
def db_stub():
    """Provide a minimal DB-like object for service contract tests."""
    return _DBStub()


@pytest.fixture
def workflow_payload():
    """Provide workflow payload fixture used by service tests."""
    return {
        "nodes": [],
        "edges": [],
    }


@pytest.fixture
def tx_payload():
    """Provide import/export payload fixture used by service tests."""
    return {
        "items": [
            {
                "product_id": 1,
                "quantity": 2,
                "unit_price": 10.0,
            }
        ]
    }
