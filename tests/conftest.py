"""Shared pytest fixtures for San Xuat's test suite.

Postgres-only (Neon sanxuat_business, same DB as the running app — no
SQLite fallback and no isolated temp DB). Every test in this suite runs
against real data; nothing here rolls back or auto-cleans, so tests that
insert rows should use throwaway-tagged values and are expected to leave
some data behind. `logged_in_client` fakes an authenticated session by
monkeypatching `core.auth_db.get_user_by_id` and pre-seeding the Flask
session, since sign-in itself happens on the separate Gateway app.
"""
import pytest

from core.config import Config


@pytest.fixture(scope="module")
def app():
    # SEC-02: give every internal-endpoint test a valid webhook token via
    # the `client` fixture below, instead of hand-editing ~20 existing
    # client.post(...) call sites across the suite.
    Config.ANSER_WEBHOOK_TOKEN = 'test-webhook-token'

    from core.sanxuat_db import init_db
    init_db()

    from app import app as flask_app

    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    yield flask_app


@pytest.fixture(scope="module")
def client(app):
    test_client = app.test_client()
    # Werkzeug's test Client merges environ_base into every request made
    # through this client -- this one line makes every existing internal-
    # endpoint call site (tests/test_n8n_internal.py, test_brain_mock.py,
    # test_expiry_alert.py) automatically carry a valid SEC-02 token with
    # zero edits to those files.
    test_client.environ_base['HTTP_X_ANSER_TOKEN'] = 'test-webhook-token'
    return test_client


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
