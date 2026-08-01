"""San Xuat's own business database — fully separate from ANSER's.

Only the `users` table (read via core/auth_db.py) is shared; everything
below is private to this app. Postgres-only (Neon sanxuat_business) — a
*different* Neon database than the shared auth one, never the same as
Retail's. No SQLite fallback; SANXUAT_POSTGRES_URL is required.
"""
import re
from datetime import datetime

from core.config import Config


SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    unit TEXT DEFAULT 'cái',
    price REAL DEFAULT 0,
    stock_quantity INTEGER DEFAULT 0,
    description TEXT,
    image_url TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    notes TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS import_transactions (
    id SERIAL PRIMARY KEY,
    code TEXT,
    supplier_name TEXT,
    total_amount REAL DEFAULT 0,
    notes TEXT,
    status TEXT DEFAULT 'completed',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS import_details (
    id SERIAL PRIMARY KEY,
    import_id INTEGER NOT NULL,
    product_id INTEGER,
    quantity REAL DEFAULT 0,
    unit_price REAL DEFAULT 0,
    total_price REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS export_transactions (
    id SERIAL PRIMARY KEY,
    code TEXT,
    customer_id INTEGER,
    total_amount REAL DEFAULT 0,
    notes TEXT,
    status TEXT DEFAULT 'completed',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS export_details (
    id SERIAL PRIMARY KEY,
    export_id INTEGER NOT NULL,
    product_id INTEGER,
    quantity REAL DEFAULT 0,
    unit_price REAL DEFAULT 0,
    total_price REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS automation_events (
    id SERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- production_orders table (real backend for the Phase 1 mock in static/js/store.js).
-- code is id-derived ('DH-' || (1000+id)) so it's set via UPDATE right after
-- INSERT, once the id is known (see routes/production_routes.py).
CREATE TABLE IF NOT EXISTS production_orders (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE,
    product_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT DEFAULT 'cái',
    customer_name TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by INTEGER,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP
);

-- production_order_events: per-order timeline ("Nhật ký quy trình" panel on
-- production-order-detail.html) — system-generated create + transition
-- events, populated by routes/production_routes.py.
CREATE TABLE IF NOT EXISTS production_order_events (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    event TEXT NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- bom_lines: master-data BOM (bill of materials) per product_code, full-
-- replaced on every save (routes/production_routes.py's PUT /api/bom/<code>
-- deletes all rows for a product then bulk-inserts the cleaned list).
CREATE TABLE IF NOT EXISTS bom_lines (
    id SERIAL PRIMARY KEY,
    product_code TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    unit TEXT DEFAULT 'cái',
    unit_cost REAL DEFAULT 0,
    qty_per_unit REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bom_lines_product_code ON bom_lines(product_code);

-- suppliers: master data for material_batches.supplier_id. code is
-- id-derived ('NCC-' || zero-padded 3-digit id), set via UPDATE right after
-- INSERT once the id is known (see routes/*_routes.py), same pattern as
-- production_orders.code.
CREATE TABLE IF NOT EXISTS suppliers (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE,
    name TEXT NOT NULL,
    contact TEXT,
    phone TEXT,
    email TEXT,
    address TEXT,
    notes TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP
);

-- material_batches: real backend for the mock's materialBatches array.
-- batch_code is id-derived ('LO-' || (2000+id)). supplier_id/material_product_id/
-- location_id are nullable FKs (no REFERENCES clause, matching this app's
-- existing tables' style, e.g. production_order_events.order_id).
-- material_product_id is resolved/auto-created from MATERIALS_CATALOG the
-- same way supplier_id is resolved from a free-text supplier name (NVL is
-- modeled as a product too). qc_status/qc_note are reserved for Phase 3
-- (QC-01) -- no route this phase writes to them.
CREATE TABLE IF NOT EXISTS material_batches (
    id SERIAL PRIMARY KEY,
    batch_code TEXT UNIQUE,
    material_code TEXT NOT NULL,
    material_name TEXT NOT NULL,
    material_product_id INTEGER,
    unit TEXT DEFAULT 'cái',
    supplier_id INTEGER,
    quantity REAL NOT NULL,
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_date TEXT,
    qc_status TEXT NOT NULL DEFAULT 'pending',
    qc_note TEXT DEFAULT '',
    location_id INTEGER,
    notes TEXT DEFAULT '',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_material_batches_material_code ON material_batches(material_code);
CREATE INDEX IF NOT EXISTS idx_material_batches_supplier_id ON material_batches(supplier_id);

-- Migration for a material_batches table that already exists from before
-- batch_code/import_date/material_product_id/location_id existed (the
-- CREATE TABLE IF NOT EXISTS above is a no-op against it) -- renames are
-- guarded so this stays a no-op on repeat runs, same idempotency guarantee
-- as the rest of this schema.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'material_batches' AND column_name = 'code')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'material_batches' AND column_name = 'batch_code') THEN
        ALTER TABLE material_batches RENAME COLUMN code TO batch_code;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'material_batches' AND column_name = 'received_at')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'material_batches' AND column_name = 'import_date') THEN
        ALTER TABLE material_batches RENAME COLUMN received_at TO import_date;
    END IF;
END $$;

ALTER TABLE material_batches ADD COLUMN IF NOT EXISTS material_product_id INTEGER;
ALTER TABLE material_batches ADD COLUMN IF NOT EXISTS location_id INTEGER;

-- suppliers table already had every column this task's spec asks for
-- (id/name/contact/phone/email/address/notes) -- only the FK constraint
-- itself was missing. No orphaned supplier_id values existed at the time
-- this was added (confirmed against the real sanxuat_business data before
-- writing this), so a straight ADD CONSTRAINT is safe; guarded so re-running
-- init_db() doesn't error on "constraint already exists".
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_material_batches_supplier_id'
    ) THEN
        ALTER TABLE material_batches
            ADD CONSTRAINT fk_material_batches_supplier_id
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id);
    END IF;
END $$;

-- production_costs: giá thành + hao hụt theo lô/ca sản xuất. Đích lưu trữ
-- dự kiến cho báo cáo mà quy trình n8n manuf_waste_profit_report tạo ra
-- (webhook POST .../production-report-insert) -- action đó hiện chưa có
-- trong _REAL_TABLE_ACTIONS (routes/n8n_api.py) nên vẫn rơi vào
-- automation_events sink chung; nối route vào bảng này nằm ngoài phạm vi
-- việc tạo bảng.
CREATE TABLE IF NOT EXISTS production_costs (
    id SERIAL PRIMARY KEY,
    production_order_id INTEGER NOT NULL,
    material_cost REAL NOT NULL DEFAULT 0,
    labor_cost REAL NOT NULL DEFAULT 0,
    waste_quantity REAL NOT NULL DEFAULT 0,
    waste_cost REAL NOT NULL DEFAULT 0,
    total_cost REAL NOT NULL DEFAULT 0,
    profit_estimate REAL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_production_costs_production_order_id ON production_costs(production_order_id);

-- invoice_attachments: file metadata only -- actual files live on disk
-- under uploads/, never as a DB blob (decision per this table's own spec:
-- Postgres stores file_path, not file bytes). ref_type is 'import' /
-- 'export' / 'material_batch', ref_id points to that record's id (no
-- REFERENCES since it targets 3 different tables depending on ref_type).
-- Column is created_by (not uploaded_by) to match routes/invoice_routes.py
-- (INVOICE-02), the real feature that writes to this table.
CREATE TABLE IF NOT EXISTS invoice_attachments (
    id SERIAL PRIMARY KEY,
    ref_type TEXT NOT NULL,
    ref_id INTEGER,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_type TEXT,
    size_bytes INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER
);

CREATE INDEX IF NOT EXISTS idx_invoice_attachments_ref ON invoice_attachments(ref_type, ref_id);

-- user_permissions: San Xuat's own role/scope layer on top of Gateway's
-- shared `users` table (read-only via core/auth_db.py, a physically
-- separate database -- see AUTH_POSTGRES_URL in core/config.py). user_id
-- is a plain INTEGER, deliberately NOT a real FOREIGN KEY: Gateway's users
-- table lives in a different Postgres database entirely, cross-database
-- FKs aren't possible. role is San-Xuat-specific (qc/kho/quan_ly_san_xuat/
-- admin), distinct from Gateway's own generic users.role column. scope is
-- a JSON-encoded permission list stored as TEXT (app layer does
-- json.dumps/json.loads), matching this schema's existing convention for
-- JSON-shaped columns (e.g. automation_events.payload) -- no JSONB type
-- used anywhere else in this app.
CREATE TABLE IF NOT EXISTS user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    scope TEXT
);

CREATE INDEX IF NOT EXISTS idx_user_permissions_user_id ON user_permissions(user_id);

-- Undo: an earlier iteration of this schema renamed invoice_attachments'
-- created_by -> uploaded_by before routes/invoice_routes.py (INVOICE-02,
-- the real feature writing to this table) was known to depend on
-- created_by. Rename it back on any DB where that earlier rename already
-- ran (guarded, so this is a no-op everywhere else, including fresh DBs).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoice_attachments' AND column_name = 'uploaded_by')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'invoice_attachments' AND column_name = 'created_by') THEN
        ALTER TABLE invoice_attachments RENAME COLUMN uploaded_by TO created_by;
    END IF;
END $$;

-- batch_usage: links a material_batches row to the production_orders row
-- that consumed it, with quantity -- 2-way traceability (lo NVL -> cac don
-- da dung no, va don san xuat -> cac lo NVL da dung), independent of
-- TRACE-02's existing BOM-membership heuristic in routes/inventory_routes.py.
CREATE TABLE IF NOT EXISTS batch_usage (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    quantity_used REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_batch_usage_batch_id ON batch_usage(batch_id);
CREATE INDEX IF NOT EXISTS idx_batch_usage_order_id ON batch_usage(order_id);

-- warehouses: unlike batches/suppliers, code is client-supplied at creation
-- time (NOT NULL), not server-generated.
CREATE TABLE IF NOT EXISTS warehouses (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    address TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS warehouse_locations (
    id SERIAL PRIMARY KEY,
    warehouse_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_warehouse_locations_warehouse_id ON warehouse_locations(warehouse_id);

-- stock_ledger: append-only / event-sourced. Every write is an INSERT;
-- current stock is always derived via SUM(quantity_delta), never a
-- mutated column. change_type in ('transfer_out', 'transfer_in',
-- 'adjustment', ...) -- import/export/transfer/adjustment per the table's
-- spec is this column's intended vocabulary going forward; transfer_stock()
-- still writes the existing 'transfer_out'/'transfer_in' pair (kept as-is,
-- not remapped, to avoid changing that route's working logic). product_id/
-- batch_id/ref_type/ref_id are optional attribution (which product/batch/
-- source-document this line traces back to), nullable since not every
-- caller has one to give. transfer_group is shared by a transfer's 2 rows,
-- NULL for adjustment rows. counterparty_warehouse_id/counterparty_location_id
-- are transfer-only; system_qty_snapshot/counted_qty are adjustment-only.
CREATE TABLE IF NOT EXISTS stock_ledger (
    id SERIAL PRIMARY KEY,
    change_type TEXT NOT NULL,
    product_id INTEGER,
    batch_id INTEGER,
    warehouse_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    product_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    unit TEXT DEFAULT 'cái',
    quantity_delta REAL NOT NULL,
    ref_type TEXT,
    ref_id INTEGER,
    transfer_group TEXT,
    counterparty_warehouse_id INTEGER,
    counterparty_location_id INTEGER,
    system_qty_snapshot REAL,
    counted_qty REAL,
    note TEXT DEFAULT '',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_stock_ledger_wlp ON stock_ledger(warehouse_id, location_id, product_code);
CREATE INDEX IF NOT EXISTS idx_stock_ledger_transfer_group ON stock_ledger(transfer_group);

-- Migration for a stock_ledger table that already exists from before
-- change_type/product_id/batch_id/ref_type/ref_id existed (same guarded-
-- rename idempotency pattern as material_batches'/qc_results' migrations).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'stock_ledger' AND column_name = 'entry_type')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'stock_ledger' AND column_name = 'change_type') THEN
        ALTER TABLE stock_ledger RENAME COLUMN entry_type TO change_type;
    END IF;
END $$;

ALTER TABLE stock_ledger ADD COLUMN IF NOT EXISTS product_id INTEGER;
ALTER TABLE stock_ledger ADD COLUMN IF NOT EXISTS batch_id INTEGER;
ALTER TABLE stock_ledger ADD COLUMN IF NOT EXISTS ref_type TEXT;
ALTER TABLE stock_ledger ADD COLUMN IF NOT EXISTS ref_id INTEGER;

-- qc_results: immutable audit log for QC-01 (Phase 2.1). Never UPDATEd or
-- DELETEd -- the "current" QC status lives on material_batches.qc_status/
-- qc_note (dual-write, populated in the same transaction by 02.1-02's
-- POST .../qc-result route, AND independently enforced by the trigger
-- below); this table is history only. No is_deleted column by design
-- (append-only, matching production_order_events' exact precedent).
-- result is 'pass'/'fail' (short form, this table's own vocabulary) --
-- distinct from material_batches.qc_status's 'pending'/'passed'/'failed'.
CREATE TABLE IF NOT EXISTS qc_results (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER NOT NULL,
    tested_by TEXT,
    test_type TEXT,
    result TEXT NOT NULL,
    detail TEXT DEFAULT '',
    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qc_results_batch_id ON qc_results(batch_id);

-- Migration for a qc_results table that already exists from before
-- tested_by/test_type/result/detail/tested_at existed (same guarded-rename
-- idempotency pattern as material_batches' migration above).
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'qc_results' AND column_name = 'qc_status')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'qc_results' AND column_name = 'result') THEN
        ALTER TABLE qc_results RENAME COLUMN qc_status TO result;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'qc_results' AND column_name = 'qc_note')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'qc_results' AND column_name = 'detail') THEN
        ALTER TABLE qc_results RENAME COLUMN qc_note TO detail;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'qc_results' AND column_name = 'created_at')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'qc_results' AND column_name = 'tested_at') THEN
        ALTER TABLE qc_results RENAME COLUMN created_at TO tested_at;
    END IF;
END $$;

ALTER TABLE qc_results ADD COLUMN IF NOT EXISTS tested_by TEXT;
ALTER TABLE qc_results ADD COLUMN IF NOT EXISTS test_type TEXT;

-- Trigger: a qc_results row inserted with result='fail' blocks that batch
-- from production use by forcing material_batches.qc_status='failed',
-- independent of whichever route/script performed the INSERT (the Python
-- routes below also set it explicitly in the same request -- this trigger
-- is the authoritative enforcement, not just a convenience mirror).
CREATE OR REPLACE FUNCTION fn_qc_results_fail_blocks_batch() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.result = 'fail' THEN
        UPDATE material_batches SET qc_status = 'failed' WHERE id = NEW.batch_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_qc_results_fail_blocks_batch ON qc_results;
CREATE TRIGGER trg_qc_results_fail_blocks_batch
    AFTER INSERT ON qc_results
    FOR EACH ROW
    EXECUTE FUNCTION fn_qc_results_fail_blocks_batch();

-- material_batch_events: append-only process-event log for QC-03/QC-04
-- (Phase 2.1), structurally identical to production_order_events
-- (batch_id instead of order_id). No enum/CHECK constraint on `event` --
-- the mock's own addProcessEvent never validates its event string either.
CREATE TABLE IF NOT EXISTS material_batch_events (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER NOT NULL,
    event TEXT NOT NULL,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_material_batch_events_batch_id ON material_batch_events(batch_id);

-- batch_process_logs: standardized process-event log per production order
-- (fixed event_type enum + logged_by attribution) -- deliberately separate
-- from production_order_events (free-text Vietnamese UI timeline, no
-- logged_by); not wired to any route yet, same as batch_usage.
CREATE TABLE IF NOT EXISTS batch_process_logs (
    id SERIAL PRIMARY KEY,
    production_order_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    note TEXT,
    logged_by INTEGER,
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_batch_process_logs_production_order_id ON batch_process_logs(production_order_id);

-- retail_warehouses / retail_storage_locations: a separate, simpler
-- single-location-per-record warehouse model "theo mẫu ANSER Bán lẻ" (low-
-- stock Discord alerting via discord_webhook_url) -- deliberately named
-- apart from warehouses/warehouse_locations/stock_ledger's existing
-- multi-location, event-sourced system (TRACE-03/04/05) so it doesn't
-- collide with it; that system intentionally never reconciles with a
-- single warehouse/location per product (see routes/warehouse_routes.py's
-- Pitfall 4 docstring).
CREATE TABLE IF NOT EXISTS retail_warehouses (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    low_stock_threshold REAL DEFAULT 0,
    discord_webhook_url TEXT
);

CREATE TABLE IF NOT EXISTS retail_storage_locations (
    id SERIAL PRIMARY KEY,
    warehouse_id INTEGER NOT NULL,
    zone TEXT,
    shelf_code TEXT
);

CREATE INDEX IF NOT EXISTS idx_retail_storage_locations_warehouse_id ON retail_storage_locations(warehouse_id);

-- material_batches already has an unrelated `location_id` column (loosely
-- tied to warehouse_locations from an earlier task) -- these use distinct
-- names (retail_warehouse_id/retail_location_id) to avoid colliding with it.
ALTER TABLE material_batches ADD COLUMN IF NOT EXISTS retail_warehouse_id INTEGER;
ALTER TABLE material_batches ADD COLUMN IF NOT EXISTS retail_location_id INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS retail_warehouse_id INTEGER;
ALTER TABLE products ADD COLUMN IF NOT EXISTS retail_location_id INTEGER;
"""


# ---------------------------------------------------------------------------
# PGShim — lets Postgres be used through the exact same sqlite3-style API
# (conn.execute(...), '?' placeholders, cur.lastrowid, row['col']) that
# every route in this app already uses, so route code never has to know
# which backend it's talking to.
# ---------------------------------------------------------------------------

_PG_PLACEHOLDER_RE = re.compile(
    r"'(?:[^'\\]|\\.)*'"
    r'|"(?:[^"\\]|\\.)*"'
    r'|(\?)',
    re.DOTALL,
)


def _to_pg(query):
    return _PG_PLACEHOLDER_RE.sub(
        lambda m: '%s' if m.group(1) is not None else m.group(0),
        query,
    )


class _PGShimCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None
        self.rowcount = -1

    def execute(self, query, params=None):
        has_params = params is not None and len(params) > 0
        query = _to_pg(query)
        is_insert = query.strip().upper().startswith('INSERT')
        try:
            if is_insert and 'RETURNING' not in query.upper():
                query += " RETURNING id"
                self._cursor.execute(query, params) if has_params else self._cursor.execute(query)
                row = self._cursor.fetchone()
                if row:
                    self.lastrowid = row['id']
            else:
                self._cursor.execute(query, params) if has_params else self._cursor.execute(query)
                self.lastrowid = None
            self.rowcount = self._cursor.rowcount
            return self
        except Exception as e:
            if is_insert and 'RETURNING id' in query:
                try:
                    if hasattr(self._cursor, 'connection'):
                        self._cursor.connection.rollback()
                except Exception:
                    pass
                clean_query = query.replace(" RETURNING id", "")
                self._cursor.execute(clean_query, params) if has_params else self._cursor.execute(clean_query)
                self.lastrowid = None
                return self
            raise e

    def executescript(self, script):
        self._cursor.execute(script)
        return self

    def fetchone(self): return self._cursor.fetchone()
    def fetchall(self): return self._cursor.fetchall()
    def fetchmany(self, size=None): return self._cursor.fetchmany(size)
    def close(self): self._cursor.close()
    def __getattr__(self, name): return getattr(self._cursor, name)


class _PGShimConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        import psycopg2.extras
        return _PGShimCursor(self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor))

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def executescript(self, script):
        cur = self.cursor()
        cur.executescript(script)
        return cur

    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self):
        try:
            self._conn.rollback()
        except Exception:
            pass
        self._conn.close()


def get_connection():
    assert Config.SANXUAT_POSTGRES_URL, (
        "SANXUAT_POSTGRES_URL is not set — this app is Postgres-only (Neon "
        "sanxuat_business), there is no SQLite fallback."
    )
    import psycopg2
    conn = psycopg2.connect(Config.SANXUAT_POSTGRES_URL)
    return _PGShimConnection(conn)


def init_db():
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_PG)
        conn.commit()
    finally:
        conn.close()


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
