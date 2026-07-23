"""Migration-chain + SQLite/Postgres schema-parity tests for migration 005."""

import runpy
import sqlite3
import os


_MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'migrations', 'versions',
    '005_invoice_draft_columns.py',
)


def test_migration_005_chains_after_004():
    # filename starts with a digit, so import via runpy.run_path, not `import`
    module_globals = runpy.run_path(_MIGRATION_PATH)
    assert module_globals['revision'] == '005'
    assert module_globals['down_revision'] == '004'
    assert callable(module_globals['upgrade'])
    assert callable(module_globals['downgrade'])


def test_sqlite_dev_schema_has_invoice_draft_columns(sqlite_db):
    conn = sqlite3.connect(sqlite_db.db_path)
    try:
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(import_transactions)")
        tx_columns = {row[1] for row in cursor.fetchall()}
        assert 'source' in tx_columns
        assert 'raw_ocr_json' in tx_columns

        cursor.execute("PRAGMA table_info(import_details)")
        detail_columns = {row[1] for row in cursor.fetchall()}
        assert 'raw_name' in detail_columns
        assert 'is_reduced_vat' in detail_columns
    finally:
        conn.close()
