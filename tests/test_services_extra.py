"""Additional service coverage — user_service, workspace_service, wallet_service."""
import json
import sqlite3

import pytest

import core.services.user_service as user_svc
import core.services.workspace_service as ws_svc
import core.services.wallet_service as wallet_svc
from core.db.user_repo import UserRepo


# ── helpers ───────────────────────────────────────────────────────────────────

def _conn_with_schema(*ddl_stmts):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for stmt in ddl_stmts:
        conn.execute(stmt)
    conn.commit()
    return conn


_USERS_DDL = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT DEFAULT 'x',
        password_version INTEGER DEFAULT 1,
        name TEXT,
        role TEXT DEFAULT 'user',
        first_name TEXT,
        last_name TEXT,
        manager_id INTEGER,
        subscription_expires_at TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )"""

_WORKSPACES_DDL = """
    CREATE TABLE workspaces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        type TEXT DEFAULT 'personal',
        description TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )"""

_ITEMS_DDL = """
    CREATE TABLE items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        type TEXT DEFAULT 'task',
        status TEXT DEFAULT 'todo',
        priority TEXT DEFAULT 'medium',
        assignee_id INTEGER,
        due_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )"""

_WALLETS_DDL = """
    CREATE TABLE wallets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        balance REAL DEFAULT 0,
        currency TEXT DEFAULT 'VND',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )"""

_WALLET_TX_DDL = """
    CREATE TABLE wallet_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        currency TEXT DEFAULT 'VND',
        type TEXT,
        status TEXT DEFAULT 'pending',
        method TEXT,
        reference TEXT,
        notes TEXT,
        metadata TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )"""

_SUBS_DDL = """
    CREATE TABLE manager_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        subscription_type TEXT,
        amount REAL,
        start_date TEXT,
        end_date TEXT,
        status TEXT DEFAULT 'inactive',
        auto_renew INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )"""


# ── mock db_manager ───────────────────────────────────────────────────────────

class _PersistentConn:
    """Connection wrapper whose close() is a no-op so the shared in-memory DB survives."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self): return self._conn.cursor()
    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self): pass  # intentional no-op
    def execute(self, *a, **kw): return self._conn.execute(*a, **kw)
    def executescript(self, *a): return self._conn.executescript(*a)

    @property
    def row_factory(self): return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, v): self._conn.row_factory = v


class _DBMock:
    """Minimal db_manager mock backed by a real SQLite connection."""

    def __init__(self, conn):
        self._conn = conn
        self.use_postgres = False

    def get_connection(self):
        return _PersistentConn(self._conn)

    def get_business_connection(self):
        return _PersistentConn(self._conn)

    def get_table_columns(self, table_name, cursor=None):
        c = cursor or self._conn.cursor()
        c.execute(f"PRAGMA table_info({table_name})")
        return [r["name"] for r in c.fetchall()]

    def log_activity(self, *args, **kwargs):
        return True

    # ── UserRepo delegation ───────────────────────────────────────────────────

    def _repo(self):
        from core.db.user_repo import UserRepo
        return UserRepo(self._conn)

    def get_all_users(self, role_filter=None):
        return self._repo().get_all_users(role_filter)

    def get_user_by_id(self, user_id):
        return self._repo().get_user_by_id(user_id)

    def delete_user(self, user_id):
        return self._repo().delete_user(user_id)

    def set_user_role(self, user_id, new_role):
        return self._repo().set_user_role(user_id, new_role)

    def update_password(self, user_id, hashed_password, version=1):
        return self._repo().update_password(user_id, hashed_password, version)


# ── user_service ──────────────────────────────────────────────────────────────

@pytest.fixture()
def user_conn():
    return _conn_with_schema(_USERS_DDL, _WORKSPACES_DDL)


@pytest.fixture()
def patched_user_svc(user_conn, monkeypatch):
    monkeypatch.setattr(user_svc, "db_manager", _DBMock(user_conn))
    return user_conn


def _seed_user(conn, email, role="user"):
    conn.execute(
        "INSERT INTO users (email, role, name) VALUES (?, ?, ?)",
        (email, role, email.split("@")[0]),
    )
    conn.commit()
    return conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]


def test_user_get_all_users_empty(patched_user_svc):
    assert user_svc.get_all_users() == []


def test_user_get_all_users_returns_list(patched_user_svc):
    _seed_user(patched_user_svc, "a@test.com")
    _seed_user(patched_user_svc, "b@test.com")
    users = user_svc.get_all_users()
    assert len(users) == 2
    assert all("email" in u for u in users)


def test_user_get_all_users_role_filter(patched_user_svc):
    _seed_user(patched_user_svc, "admin@test.com", role="admin")
    _seed_user(patched_user_svc, "user@test.com", role="user")
    admins = user_svc.get_all_users(role_filter="admin")
    assert len(admins) == 1
    assert admins[0]["role"] == "admin"


def test_user_delete_regular_user(patched_user_svc):
    uid = _seed_user(patched_user_svc, "del@test.com", role="user")
    user_svc.delete_user(uid)
    assert user_svc.get_all_users() == []


def test_user_delete_non_user_role_raises(patched_user_svc):
    uid = _seed_user(patched_user_svc, "mgr@test.com", role="manager")
    with pytest.raises(PermissionError):
        user_svc.delete_user(uid)


def test_user_delete_missing_raises(patched_user_svc):
    with pytest.raises(LookupError):
        user_svc.delete_user(9999)


def test_user_set_role(patched_user_svc):
    uid = _seed_user(patched_user_svc, "role@test.com", role="user")
    user_svc.set_user_role(uid, "manager", actor_id=0, actor_ip="127.0.0.1", action_label="promote")
    row = patched_user_svc.execute("SELECT role FROM users WHERE id = ?", (uid,)).fetchone()
    assert row["role"] == "manager"


def test_user_set_role_on_admin_raises(patched_user_svc):
    uid = _seed_user(patched_user_svc, "admin2@test.com", role="admin")
    with pytest.raises(PermissionError):
        user_svc.set_user_role(uid, "user", actor_id=0, actor_ip="", action_label="demote")


def test_user_reset_password(patched_user_svc, monkeypatch):
    uid = _seed_user(patched_user_svc, "reset@test.com")
    user_svc.reset_password(uid, "newpassword123")
    row = patched_user_svc.execute("SELECT password FROM users WHERE id = ?", (uid,)).fetchone()
    assert row["password"] != "x"  # password was hashed and updated


def test_user_reset_password_missing_raises(patched_user_svc):
    with pytest.raises(LookupError):
        user_svc.reset_password(9999, "pw")


# ── UserRepo direct ───────────────────────────────────────────────────────────

def test_user_repo_get_all_with_permissions(user_conn):
    _seed_user(user_conn, "repo@test.com", role="user")
    repo = UserRepo(user_conn)
    users = repo.get_all_users_with_permissions()
    assert len(users) == 1
    assert users[0]["permissions"] == []


def test_user_repo_get_workspaces(user_conn):
    uid = _seed_user(user_conn, "ws@test.com")
    user_conn.execute(
        "INSERT INTO workspaces (user_id, name, type) VALUES (?, 'My WS', 'personal')",
        (uid,),
    )
    user_conn.commit()
    repo = UserRepo(user_conn)
    workspaces = repo.get_user_workspaces(uid)
    assert len(workspaces) == 1


# ── workspace_service ─────────────────────────────────────────────────────────

@pytest.fixture()
def ws_conn():
    return _conn_with_schema(_USERS_DDL, _WORKSPACES_DDL, _ITEMS_DDL)


@pytest.fixture()
def patched_ws_svc(ws_conn, monkeypatch):
    monkeypatch.setattr(ws_svc, "db_manager", _DBMock(ws_conn))
    return ws_conn


def _seed_workspace(conn, user_id=1, name="WS"):
    conn.execute(
        "INSERT INTO users (id, email, role) VALUES (?, ?, 'user') ON CONFLICT DO NOTHING",
        (user_id, f"u{user_id}@test.com"),
    )
    conn.commit()
    return ws_svc.create_workspace(user_id, name, "personal", "desc")


def test_ws_create_workspace(patched_ws_svc):
    wid = ws_svc.create_workspace(1, "My WS", "personal", "test")
    assert isinstance(wid, int)


def test_ws_get_items_empty(patched_ws_svc):
    wid = _seed_workspace(patched_ws_svc)
    patched_ws_svc.execute(
        "INSERT INTO users (id, email, role) VALUES (1, 'u@t.com', 'user') ON CONFLICT DO NOTHING"
    )
    patched_ws_svc.commit()
    items = ws_svc.get_workspace_items(wid, user_id=1)
    assert items == []


def test_ws_create_and_get_item(patched_ws_svc):
    patched_ws_svc.execute(
        "INSERT INTO users (id, email, role) VALUES (1, 'u@t.com', 'user') ON CONFLICT DO NOTHING"
    )
    patched_ws_svc.commit()
    wid = ws_svc.create_workspace(1, "WS", "personal", "")
    ws_svc.create_item(wid, 1, "Task A", "desc", "task", "todo", "medium")
    items = ws_svc.get_workspace_items(wid, user_id=1)
    assert len(items) == 1
    assert items[0]["title"] == "Task A"


def test_ws_create_item_wrong_user_raises(patched_ws_svc):
    patched_ws_svc.execute(
        "INSERT INTO users (id, email, role) VALUES (1, 'u@t.com', 'user') ON CONFLICT DO NOTHING"
    )
    patched_ws_svc.commit()
    wid = ws_svc.create_workspace(1, "WS", "personal", "")
    with pytest.raises(PermissionError):
        ws_svc.create_item(wid, user_id=99, title="X", description="",
                           item_type="task", status="todo", priority="low")


def test_ws_update_item(patched_ws_svc):
    patched_ws_svc.execute(
        "INSERT INTO users (id, email, role) VALUES (1, 'u@t.com', 'user') ON CONFLICT DO NOTHING"
    )
    patched_ws_svc.commit()
    wid = ws_svc.create_workspace(1, "WS", "personal", "")
    item_id = ws_svc.create_item(wid, 1, "Old Title", "", "task", "todo", "medium")
    ws_svc.update_item(item_id, 1, "New Title", "updated desc", "done", "high")
    items = ws_svc.get_workspace_items(wid, user_id=1)
    assert items[0]["status"] == "done"


def test_ws_delete_item(patched_ws_svc):
    patched_ws_svc.execute(
        "INSERT INTO users (id, email, role) VALUES (1, 'u@t.com', 'user') ON CONFLICT DO NOTHING"
    )
    patched_ws_svc.commit()
    wid = ws_svc.create_workspace(1, "WS", "personal", "")
    item_id = ws_svc.create_item(wid, 1, "Delete Me", "", "task", "todo", "low")
    ws_svc.delete_item(item_id, user_id=1)
    assert ws_svc.get_workspace_items(wid, user_id=1) == []


# ── wallet_service ────────────────────────────────────────────────────────────

@pytest.fixture()
def wallet_conn(monkeypatch):
    from core.config import Config
    monkeypatch.setattr(Config, "USE_POSTGRES", False)
    return _conn_with_schema(_WALLETS_DDL, _WALLET_TX_DDL, _SUBS_DDL)


def test_wallet_get_data_creates_wallet(wallet_conn):
    data = wallet_svc.get_wallet_data(wallet_conn, user_id=1)
    assert data["wallet"]["balance"] == 0
    assert data["wallet"]["currency"] == "VND"
    assert data["subscription"] is None
    assert data["transactions"] == []


def test_wallet_topup_request_persists(wallet_conn):
    wallet_svc.create_topup_request(
        wallet_conn, user_id=1, amount=100000,
        method="bank_transfer", reference="REF001", note="top up",
    )
    row = wallet_conn.execute(
        "SELECT status, amount FROM wallet_transactions WHERE user_id = 1"
    ).fetchone()
    assert row["status"] == "pending"
    assert row["amount"] == 100000


def test_wallet_topup_minimum_amount_raises(wallet_conn):
    with pytest.raises(ValueError, match="Minimum"):
        wallet_svc.create_topup_request(wallet_conn, 1, 1000, "bank", "", "")


def test_wallet_withdrawal_insufficient_balance_raises(wallet_conn):
    with pytest.raises(ValueError, match="Insufficient"):
        wallet_svc.create_withdrawal(wallet_conn, 1, 500000, "VCB", "123", "Me", "")


def test_wallet_toggle_auto_renew_no_subscription_raises(wallet_conn):
    with pytest.raises(ValueError, match="No subscription"):
        wallet_svc.toggle_auto_renew(wallet_conn, user_id=1, enabled=True)
