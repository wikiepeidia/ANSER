"""Add invoice-draft columns for the VLM write-back endpoint.

`POST /api/n8n/internal/invoice-import-draft` (v1.1 Phase 2) needs a place to
store the VLM-extracted draft's provenance without touching any existing
column's meaning:
- `import_transactions.source` — distinguishes this write path (e.g.
  `'n8n_vlm'`) from manual UI imports.
- `import_transactions.raw_ocr_json` — the full received request body,
  stored verbatim/opaque (never parsed back out as SQL or code) for audit
  and human-review traceability.
- `import_details.raw_name` — the OCR'd line-item name, preserved even when
  it doesn't match an existing product (so an unmatched item is never
  silently dropped).
- `import_details.is_reduced_vat` — passes through Brain's
  `InvoiceItem.is_reduced_vat` field verbatim.

Revision ID: 005
Revises: 004
Create Date: 2026-07-22
"""
from alembic import op

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

_STATEMENTS = [
    "ALTER TABLE import_transactions ADD COLUMN IF NOT EXISTS source TEXT",
    "ALTER TABLE import_transactions ADD COLUMN IF NOT EXISTS raw_ocr_json TEXT",
    "ALTER TABLE import_details ADD COLUMN IF NOT EXISTS raw_name TEXT",
    "ALTER TABLE import_details ADD COLUMN IF NOT EXISTS is_reduced_vat BOOLEAN",
]


def upgrade():
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade():
    op.execute('ALTER TABLE import_details DROP COLUMN IF EXISTS is_reduced_vat')
    op.execute('ALTER TABLE import_details DROP COLUMN IF EXISTS raw_name')
    op.execute('ALTER TABLE import_transactions DROP COLUMN IF EXISTS raw_ocr_json')
    op.execute('ALTER TABLE import_transactions DROP COLUMN IF EXISTS source')
