import json
import sqlite3

from core.automation_engine import AutomationEngine
from core.db.connection import Database


class _NoCloseConnection:
    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


def make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    db = Database.__new__(Database)
    db.db_path = ":memory:"
    db.use_postgres = False
    db._pg_pool = None
    db._pg_pool_lock = None
    db.get_connection = lambda: _NoCloseConnection(conn)
    db.init_database()
    db._memory_conn = conn
    return db


def test_execute_import_automation():
    db = make_db()
    conn = db._memory_conn
    try:
        engine = AutomationEngine(db)
        c = conn.cursor()

        c.execute(
            """INSERT INTO products
               (code, name, category, unit, price, stock_quantity, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("P-TEST", "Test Product", "test", "pcs", 100.0, 5, 1),
        )
        product_id = c.lastrowid
        c.execute(
            """INSERT INTO se_automations
               (name, type, config, enabled)
               VALUES (?, ?, ?, ?)""",
            (
                "Test Auto",
                "low_stock",
                json.dumps({"threshold": 10, "reorder_quantity": 20}),
                1,
            ),
        )
        auto_id = c.lastrowid
        conn.commit()

        engine.execute_import_automation(
            auto_id,
            {"threshold": 10, "reorder_quantity": 20},
            product_id,
        )

        c.execute("SELECT COUNT(*) AS count FROM import_transactions WHERE code LIKE 'IMP-AUTO-%'")
        assert c.fetchone()["count"] >= 1
    finally:
        conn.close()


def test_execute_scheduled_import():
    db = make_db()
    conn = db._memory_conn
    try:
        engine = AutomationEngine(db)
        c = conn.cursor()

        c.execute(
            """INSERT INTO products
               (code, name, category, unit, price, stock_quantity, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("P-SCH", "Scheduled Product", "test", "pcs", 75.0, 5, 1),
        )
        c.execute(
            """INSERT INTO se_automations
               (name, type, config, enabled)
               VALUES (?, ?, ?, ?)""",
            ("Scheduled Auto", "scheduled", json.dumps({}), 1),
        )
        auto_id = c.lastrowid
        conn.commit()

        engine.execute_scheduled_import(auto_id, {})

        c.execute("SELECT COUNT(*) AS count FROM import_transactions WHERE code LIKE 'IMP-SCH-%'")
        assert c.fetchone()["count"] >= 1
    finally:
        conn.close()
