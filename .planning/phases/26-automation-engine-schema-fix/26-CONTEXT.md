# Phase 26: Automation Engine Schema Fix - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Fix `core/automation_engine.py` so it only references tables and columns that exist in the actual SQLite schema. The file currently references `import_price` column (does not exist) and `suppliers` table (does not exist). The actual schema uses `price` (products table) and `supplier_name TEXT` (import_transactions table).

**Scope:**
- `core/automation_engine.py`: fix all references to `import_price` → `price`, remove all `SELECT id FROM suppliers` queries, fix all `INSERT INTO import_transactions` statements to use `supplier_name` instead of `supplier_id`
- `tests/` or `core/tests/`: write a smoke test that runs `execute_import_automation` and `execute_scheduled_import` against an in-memory SQLite database

**Out of scope:** Changes to the database schema itself, Flask routes, or any other files.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase.

Specific known state (from schema audit):

**`core/db/connection.py` — actual SQLite schema (relevant tables):**

`products` columns: `id, code, name, category, unit, price, stock_quantity, description, created_by, created_at, updated_at, image_url`
- Column `import_price` does NOT exist — must use `price`

`import_transactions` columns: `id, code, supplier_name, total_amount, notes, status, created_by, created_at`
- Column `supplier_id` does NOT exist — schema uses `supplier_name TEXT`
- Table `suppliers` does NOT exist

`import_details` columns: `id, import_id, product_id, quantity, unit_price, total_price`
- This table EXISTS and is correct — no changes needed

**Lines to fix in `core/automation_engine.py`:**

*In `execute_import_automation` (lines 135-173):*
- Line 145: `SELECT name, import_price FROM products WHERE id = ?` → `SELECT name, price FROM products WHERE id = ?`
- Line 147: `prod['import_price']` → `prod['price']`
- Lines 151-153: Remove the `SELECT id FROM suppliers LIMIT 1` query + `supplier_id` variable; replace with `supplier_name = 'Automated Import'`
- Lines 155-158: Change INSERT column `supplier_id` → `supplier_name`

*In `execute_scheduled_import` (lines 175-226):*
- Line 185: `SELECT id, stock_quantity, import_price FROM products` → `SELECT id, stock_quantity, price FROM products`
- Lines 194-196: Remove `SELECT id FROM suppliers LIMIT 1` query + `supplier_id` variable; replace with `supplier_name = 'Automated Import'`
- Line 203: `prod['import_price']` → `prod['price']`
- Lines 207-210: Change INSERT column `supplier_id` → `supplier_name`

</decisions>

<code_context>
## Existing Code Insights

### Schema Source
`core/db/connection.py` — `init_database()` method defines the SQLite schema via `executescript`.

### What the methods do
- `execute_import_automation(auto_id, config, product_id)` — Creates one import transaction for a single product that triggered low-stock automation
- `execute_scheduled_import(auto_id, config)` — Creates one import transaction covering all products below threshold=20

### Integration Points
- `check_low_stock()` calls `execute_import_automation()` — both are in scope for smoke test
- `execute_scheduled_import()` called by `check_scheduled_automations()` — smoke test should call it directly
- Both methods use `self.db_manager.get_connection()` — smoke test should instantiate `AutomationEngine` with a real `Database` object pointing at `:memory:`

</code_context>

<specifics>
## Specific Ideas

- Smoke test: use `from core.db.connection import Database` with `sqlite_path=':memory:'` and `use_postgres=False`; call `db.init_database()` to create schema; insert one test product; then call both methods
- For `supplier_name` default value: use `'Automated Import'` — descriptive and schema-compatible
- No new imports needed in `automation_engine.py` — all fixes are SQL string and dict-key changes

</specifics>

<deferred>
## Deferred Ideas

- Alembic migration for NeonDB (PostgreSQL path) — out of scope; AUTO-02 only requires SQLite smoke test to pass
- Adding actual supplier lookup from a config or env var — over-engineered for this phase

</deferred>
