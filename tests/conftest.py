"""Shared pytest fixtures for San Xuat's test suite.

`app`/`client` stand up the Flask app against an isolated temp SQLite DB
(never the real dev `san_xuat.db`) so tests never corrupt or depend on
local dev data. `logged_in_client` fakes an authenticated session by
monkeypatching `core.auth_db.get_user_by_id` and pre-seeding the Flask
session, since sign-in itself happens on the separate Gateway app.
"""
import os
import tempfile

import pytest

from core.config import Config


@pytest.fixture(scope="module")
def app():
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Must be patched before app.py's module-level `app = create_app()`
    # (imported below) runs init_db() against it. Force SQLite even if this
    # shared multi-branch working tree's .env defines SANXUAT_POSTGRES_URL
    # (Config.SANXUAT_USE_POSTGRES is computed from that env var at class-
    # definition time) — otherwise get_connection() would silently connect
    # to a real Neon Postgres database instead of this isolated temp file,
    # which is exactly the "never corrupt or depend on local dev data"
    # guarantee this fixture exists to provide. (Independently confirmed by
    # a teammate hitting the identical landmine — see merge commit.)
    Config.SANXUAT_DATABASE_PATH = temp_path
    Config.SANXUAT_USE_POSTGRES = False

    from core.sanxuat_db import init_db
    init_db()

    from app import app as flask_app

    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    yield flask_app

    try:
        os.remove(temp_path)
    except OSError:
        pass


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def logged_in_client(client):
    import core.auth_db as auth_db

    fake_user = {
        'id': 1,
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'role': 'manager',
        'avatar': None,
    }

    original_get_user_by_id = auth_db.get_user_by_id

    def _fake_get_user_by_id(user_id):
        if int(user_id) == 1:
            return fake_user
        return original_get_user_by_id(user_id)

    auth_db.get_user_by_id = _fake_get_user_by_id

    with client.session_transaction() as sess:
        sess["_user_id"] = "1"
        sess["_fresh"] = True

    yield client

    auth_db.get_user_by_id = original_get_user_by_id


@pytest.fixture()
def regular_user_client(app):
    """Same monkeypatch-of-auth_db pattern as `logged_in_client`, but for a
    second fake user (id=2, role='user') -- used to prove SEC-01's role
    gates actually block non-manager sessions.

    Uses its own `app.test_client()` (not the shared `client` fixture)
    because Flask test clients carry their own cookie jar/session -- reusing
    `logged_in_client`'s client here would mean `session_transaction()`
    overwrites the *same* session's `_user_id`, silently logging the manager
    session out instead of creating an independent regular-user session.
    """
    import core.auth_db as auth_db

    own_client = app.test_client()

    fake_user = {
        'id': 2,
        'email': 'regular@example.com',
        'first_name': 'Regular',
        'last_name': 'User',
        'role': 'user',
        'avatar': None,
    }

    original_get_user_by_id = auth_db.get_user_by_id

    def _fake_get_user_by_id(user_id):
        if int(user_id) == 2:
            return fake_user
        return original_get_user_by_id(user_id)

    auth_db.get_user_by_id = _fake_get_user_by_id

    with own_client.session_transaction() as sess:
        sess["_user_id"] = "2"
        sess["_fresh"] = True

    yield own_client

    auth_db.get_user_by_id = original_get_user_by_id
