"""Coverage for operations_service, subscription_service, and wallet extras."""
import sqlite3
import json

import pytest

import core.services.operations_service as ops
import core.services.subscription_service as sub_svc
import core.services.wallet_service as wallet_svc
from core.config import Config


# ── shared helpers ────────────────────────────────────────────────────────────

def _conn(*ddl):
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    for stmt in ddl:
        c.execute(stmt)
    c.commit()
    return c


class _PersistentConn:
    def __init__(self, conn):
        self._c = conn
    def cursor(self): return self._c.cursor()
    def commit(self): self._c.commit()
    def rollback(self): self._c.rollback()
    def close(self): pass
    def execute(self, *a, **kw): return self._c.execute(*a, **kw)
    @property
    def row_factory(self): return self._c.row_factory
    @row_factory.setter
    def row_factory(self, v): self._c.row_factory = v


class _DBMock:
    def __init__(self, conn):
        self._conn = conn
        self.use_postgres = False
    def get_connection(self):
        return _PersistentConn(self._conn)
    def get_business_connection(self):
        return _PersistentConn(self._conn)
    def get_table_columns(self, table, cursor=None):
        c = cursor or self._conn.cursor()
        c.execute(f"PRAGMA table_info({table})")
        return [r["name"] for r in c.fetchall()]
    def log_activity(self, *a, **kw): return True


# ── DDL snippets ──────────────────────────────────────────────────────────────

_EXPORT_TX = "CREATE TABLE export_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, total_amount REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
_IMPORT_TX = "CREATE TABLE import_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, total_amount REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
_WORKFLOWS  = "CREATE TABLE workflows (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, data TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"
_SCHEDULED_REPORTS = """CREATE TABLE scheduled_reports (
    id TEXT PRIMARY KEY, name TEXT, report_type TEXT,
    frequency TEXT, channel TEXT, recipients TEXT, status TEXT DEFAULT 'active',
    last_sent_at TEXT, created_by INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
_SE_AUTOMATIONS = """CREATE TABLE se_automations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, config TEXT,
    enabled INTEGER DEFAULT 0, last_run TEXT, created_by INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
_USERS = "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, name TEXT, role TEXT DEFAULT 'user', subscription_expires_at TEXT)"
_SUBS = """CREATE TABLE manager_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE,
    subscription_type TEXT, amount REAL, start_date TEXT, end_date TEXT,
    status TEXT DEFAULT 'inactive', auto_renew INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
_SUB_HISTORY = """CREATE TABLE subscription_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, subscription_type TEXT,
    amount REAL, payment_date TEXT, payment_method TEXT, transaction_id TEXT,
    status TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
_WALLET_TX = """CREATE TABLE wallet_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL,
    currency TEXT DEFAULT 'VND', type TEXT, status TEXT DEFAULT 'pending',
    method TEXT, reference TEXT, notes TEXT, metadata TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"""
_WALLETS = """CREATE TABLE wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE,
    balance REAL DEFAULT 0, currency TEXT DEFAULT 'VND',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP)"""


# ── operations_service ────────────────────────────────────────────────────────

@pytest.fixture()
def ops_conn(monkeypatch):
    c = _conn(_EXPORT_TX, _IMPORT_TX, _WORKFLOWS, _SCHEDULED_REPORTS, _SE_AUTOMATIONS)
    monkeypatch.setattr(ops, "db_manager", _DBMock(c))
    return c


def test_ops_dashboard_stats_empty(ops_conn):
    stats = ops.get_dashboard_stats(user_id=1)
    assert stats["revenue"] == 0
    assert stats["new_orders"] == 0
    assert stats["active_projects"] == 0


def test_ops_dashboard_counts_workflows(ops_conn):
    ops_conn.execute("INSERT INTO workflows (user_id, name) VALUES (1, 'Flow A')")
    ops_conn.execute("INSERT INTO workflows (user_id, name) VALUES (1, 'Flow B')")
    ops_conn.commit()
    stats = ops.get_dashboard_stats(user_id=1)
    assert stats["active_projects"] == 2


def test_ops_report_stats_empty(ops_conn):
    stats = ops.get_report_stats()
    assert stats["profit"] == 0


def test_ops_create_and_list_scheduled_reports(ops_conn):
    ops.create_scheduled_report("Daily Sales", "sales", "daily", "email", "a@b.com", 1)
    reports = ops.get_scheduled_reports()
    assert len(reports) == 1
    assert reports[0]["name"] == "Daily Sales"
    assert reports[0]["frequency"] == "daily"


def test_ops_delete_scheduled_report(ops_conn):
    ops.create_scheduled_report("Weekly", "sales", "weekly", "email", "x@y.com", 1)
    reports = ops.get_scheduled_reports()
    ops.delete_scheduled_report(reports[0]["id"])
    assert ops.get_scheduled_reports() == []


def test_ops_create_and_list_automations(ops_conn):
    ops.create_automation("Low Stock Alert", "low_stock", {"threshold": 5}, 1)
    automations = ops.get_automations()
    assert len(automations) == 1
    assert automations[0]["name"] == "Low Stock Alert"
    assert automations[0]["config"] == {"threshold": 5}
    assert automations[0]["enabled"] is False


def test_ops_update_automation_status(ops_conn):
    ops.create_automation("AutoRpt", "scheduled", {}, 1)
    aid = ops.get_automations()[0]["id"]
    ops.update_automation(aid, {"status": "active"})
    assert ops.get_automations()[0]["enabled"] is True


def test_ops_update_automation_name(ops_conn):
    ops.create_automation("OldName", "scheduled", {}, 1)
    aid = ops.get_automations()[0]["id"]
    ops.update_automation(aid, {"name": "NewName"})
    assert ops.get_automations()[0]["name"] == "NewName"


def test_ops_update_automation_not_found_raises(ops_conn):
    with pytest.raises(LookupError):
        ops.update_automation(9999, {"name": "X"})


def test_ops_delete_automation(ops_conn):
    ops.create_automation("ToDelete", "low_stock", {}, 1)
    aid = ops.get_automations()[0]["id"]
    ops.delete_automation(aid)
    assert ops.get_automations() == []


# ── subscription_service ──────────────────────────────────────────────────────

@pytest.fixture()
def sub_conn(monkeypatch):
    c = _conn(_USERS, _SUBS, _SUB_HISTORY, _WALLET_TX)
    monkeypatch.setattr(sub_svc, "db_manager", _DBMock(c))
    return c


def _seed_user(conn, uid=1, email="u@test.com"):
    conn.execute("INSERT INTO users (id, email, name, role) VALUES (?, ?, 'User', 'user')", (uid, email))
    conn.commit()


def test_sub_get_all_empty(sub_conn):
    assert sub_svc.get_all_subscriptions() == []


def test_sub_extend_creates_subscription(sub_conn):
    _seed_user(sub_conn)
    end = sub_svc.extend_subscription(1, "monthly", "manual")
    assert end is not None
    subs = sub_svc.get_all_subscriptions()
    assert len(subs) == 1
    assert subs[0]["subscription_type"] == "monthly"
    assert subs[0]["status"] == "active"


def test_sub_extend_invalid_plan_raises(sub_conn):
    with pytest.raises(ValueError, match="Invalid plan"):
        sub_svc.extend_subscription(1, "unknown_plan", "manual")


def test_sub_extend_stacks_from_current_end(sub_conn):
    _seed_user(sub_conn)
    end1 = sub_svc.extend_subscription(1, "monthly", "manual")
    end2 = sub_svc.extend_subscription(1, "monthly", "manual")
    assert end2 > end1


def test_sub_history_after_extend(sub_conn):
    _seed_user(sub_conn)
    sub_svc.extend_subscription(1, "trial", "free")
    history = sub_svc.get_subscription_history()
    assert len(history) >= 1


def test_sub_check_expired_no_expired(sub_conn):
    _seed_user(sub_conn)
    count = sub_svc.check_expired_subscriptions()
    assert count == 0


def test_sub_set_auto_renew(sub_conn):
    _seed_user(sub_conn)
    sub_svc.extend_subscription(1, "monthly", "manual")
    sub_svc.set_auto_renew(1, True)
    row = sub_conn.execute("SELECT auto_renew FROM manager_subscriptions WHERE user_id=1").fetchone()
    assert row["auto_renew"] == 1


# ── wallet extras ─────────────────────────────────────────────────────────────

@pytest.fixture()
def wallet_conn(monkeypatch):
    monkeypatch.setattr(Config, "USE_POSTGRES", False)
    return _conn(_WALLETS, _WALLET_TX, _SUBS)


def test_wallet_create_withdrawal_success(wallet_conn):
    # Seed balance first
    wallet_conn.execute("INSERT INTO wallets (user_id, balance) VALUES (1, 500000)")
    wallet_conn.commit()
    wallet_svc.create_withdrawal(wallet_conn, 1, 100000, "VCB", "123456", "Me", "test")
    row = wallet_conn.execute("SELECT balance FROM wallets WHERE user_id=1").fetchone()
    assert row["balance"] == pytest.approx(400000)


def test_wallet_process_transaction_approve(wallet_conn):
    wallet_conn.execute(
        "INSERT INTO wallet_transactions"
        " (user_id, amount, type, status, method, metadata)"
        " VALUES (1, 200000, 'topup', 'pending', 'bank', '{}')"
    )
    wallet_conn.commit()
    row = wallet_conn.execute("SELECT id FROM wallet_transactions").fetchone()
    wallet_svc.process_transaction(wallet_conn, row["id"], "approve", 0, "admin@test.com", "")
    status = wallet_conn.execute("SELECT status FROM wallet_transactions WHERE id=?", (row["id"],)).fetchone()
    assert status["status"] == "completed"
    balance = wallet_conn.execute("SELECT balance FROM wallets WHERE user_id=1").fetchone()
    assert balance["balance"] == pytest.approx(200000)


def test_wallet_process_transaction_reject(wallet_conn):
    wallet_conn.execute(
        "INSERT INTO wallet_transactions"
        " (user_id, amount, type, status, method, metadata)"
        " VALUES (1, 50000, 'topup', 'pending', 'bank', '{}')"
    )
    wallet_conn.commit()
    row = wallet_conn.execute("SELECT id FROM wallet_transactions").fetchone()
    wallet_svc.process_transaction(wallet_conn, row["id"], "reject", 0, "admin@test.com", "invalid")
    status = wallet_conn.execute("SELECT status FROM wallet_transactions WHERE id=?", (row["id"],)).fetchone()
    assert status["status"] == "rejected"


def test_wallet_process_already_processed_raises(wallet_conn):
    wallet_conn.execute(
        "INSERT INTO wallet_transactions (user_id, amount, type, status, method, metadata)"
        " VALUES (1, 10000, 'topup', 'completed', 'bank', '{}')"
    )
    wallet_conn.commit()
    row = wallet_conn.execute("SELECT id FROM wallet_transactions").fetchone()
    with pytest.raises(ValueError, match="already processed"):
        wallet_svc.process_transaction(wallet_conn, row["id"], "approve", 0, "a@b.com", "")
