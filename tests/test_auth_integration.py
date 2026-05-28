"""Integration tests for AuthManager + UserRepo using SQLite in-memory."""
import pytest
from core.auth import AuthManager


@pytest.fixture()
def auth(sqlite_db, monkeypatch):
    monkeypatch.setattr("core.auth.send_email", lambda *a, **kw: None)
    return AuthManager(sqlite_db)


# ── Register ──────────────────────────────────────────────────────────────────

def test_register_new_user_succeeds(auth):
    ok, msg = auth.register_user("alice@test.com", "secret123", "Alice", "Smith")
    assert ok is True


def test_register_duplicate_email_fails(auth):
    auth.register_user("bob@test.com", "pass", "Bob", "Jones")
    ok, msg = auth.register_user("bob@test.com", "other", "Bob", "Jones")
    assert ok is False


def test_register_creates_personal_workspace(auth, sqlite_db):
    auth.register_user("carol@test.com", "pw", "Carol", "White")
    conn = sqlite_db.get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) AS cnt FROM workspaces")
        assert c.fetchone()["cnt"] == 1
    finally:
        conn.close()


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_correct_password_returns_user(auth):
    auth.register_user("dave@test.com", "correct", "Dave", "Black")
    user = auth.verify_user("dave@test.com", "correct")
    assert user is not None
    assert user["email"] == "dave@test.com"
    assert "id" in user
    assert "role" in user


def test_login_wrong_password_returns_none(auth):
    auth.register_user("eve@test.com", "rightpw", "Eve", "Green")
    user = auth.verify_user("eve@test.com", "wrongpw")
    assert user is None


def test_login_nonexistent_user_returns_none(auth):
    assert auth.verify_user("ghost@test.com", "any") is None


# ── get_user_by_id ────────────────────────────────────────────────────────────

def test_get_user_by_id_after_register(auth, sqlite_db):
    auth.register_user("frank@test.com", "pw", "Frank", "Red")
    user = auth.verify_user("frank@test.com", "pw")
    fetched = sqlite_db.get_user_by_id(user["id"])
    assert fetched is not None
    assert fetched["email"] == "frank@test.com"


def test_get_user_by_id_missing_returns_none(sqlite_db):
    assert sqlite_db.get_user_by_id(99999) is None


# ── get_user_workspaces ───────────────────────────────────────────────────────

def test_get_user_workspaces_returns_list(auth, sqlite_db):
    auth.register_user("grace@test.com", "pw", "Grace", "Blue")
    user = auth.verify_user("grace@test.com", "pw")
    workspaces = sqlite_db.get_user_workspaces(user["id"])
    assert isinstance(workspaces, list)
    assert len(workspaces) == 1


# ── Legacy sha256 rehash path ─────────────────────────────────────────────────

def test_legacy_sha256_password_rehashed_on_login(auth, sqlite_db):
    """User with password_version=0 (sha256) is re-hashed on successful login."""
    import hashlib
    raw_pw = "oldpassword"
    sha_hash = hashlib.sha256(raw_pw.encode()).hexdigest()
    conn = sqlite_db.get_connection()
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (name, email, password, password_version, role)"
            " VALUES (?, ?, ?, 0, 'user')",
            ("Legacy User", "legacy@test.com", sha_hash),
        )
        conn.commit()
    finally:
        conn.close()

    user = auth.verify_user("legacy@test.com", raw_pw)
    assert user is not None
    assert user["email"] == "legacy@test.com"

    # After re-hash, password_version should be 1
    conn = sqlite_db.get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT password_version FROM users WHERE email = ?", ("legacy@test.com",))
        assert c.fetchone()["password_version"] == 1
    finally:
        conn.close()
