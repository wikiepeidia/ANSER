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
    # (imported below) runs init_db() against it. SANXUAT_USE_POSTGRES must
    # be forced off too — otherwise, whenever SANXUAT_POSTGRES_URL is set in
    # the real .env, get_connection() ignores SANXUAT_DATABASE_PATH entirely
    # and tests run against the real Neon DB instead of this temp SQLite file.
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
        'role': 'admin',
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
