"""Dedicated insert-only writer for VLM-extracted invoice import drafts.

This is deliberately a separate routine from
`inventory_tx_service.create_import_transaction()`, not a variant of it, per
02-body-write-back-endpoint's locked decision:

- `create_import_transaction()` requires an authenticated `user_id` (raises
  if `None`) — but a shared-secret automation caller (n8n) never has a user
  session, so `user_id` is always `None` here. Calling the existing function
  would hard-fail every request.
- Its INSERT never lists `status` at all, so it silently lands as the
  column's DB default (`'completed'`) — exactly the safety violation this
  endpoint exists to prevent for an unreviewed, VLM-extracted draft.
- It calls stock-adjustment helpers (`_adjust_warehouse_stock`,
  `_sync_product_total_stock`) for every matched item — live stock mutation
  that must never happen for a `pending_review` draft.

`create_invoice_draft()` below always writes `status='pending_review'` as a
literal SQL value (never a bound value sourced from the request payload),
never touches `warehouse_stock` or `products.stock_quantity`, and never
auto-creates a `products` row for an unmatched line item (an OCR misread
becomes a NULL-`product_id` row with the OCR'd name preserved in
`raw_name`, not a garbage duplicate product).
"""

import json
from datetime import datetime

from .service_errors import ServiceInvariantError, ServiceValidationError


def _require_clean_invoice(payload):
    """Validate the payload looks like a clean, reviewable invoice.

    Returns (invoice, items) on success. Raises ServiceValidationError on
    any shape/validation failure — this endpoint only ever accepts the
    clean/reviewable case, never a failure or manual-review case.
    """
    if not isinstance(payload, dict):
        raise ServiceValidationError("payload phải là một dictionary")
    if payload.get("success") is not True:
        raise ServiceValidationError("payload.success phải là true")
    if payload.get("needs_manual_review"):
        raise ServiceValidationError("needs_manual_review=true không được chấp nhận ở endpoint này")

    invoice = payload.get("invoice")
    if not isinstance(invoice, dict):
        raise ServiceValidationError("payload.invoice là bắt buộc và phải là object")

    items = invoice.get("items")
    if not isinstance(items, list) or not items:
        raise ServiceValidationError("invoice.items là bắt buộc và không được rỗng")

    if "total" not in invoice:
        raise ServiceValidationError("invoice.total là bắt buộc")

    return invoice, items


def create_invoice_draft(db_conn, payload):
    """Insert a pending_review import draft from a clean VLM invoice payload.

    Only DB statements issued: one INSERT INTO import_transactions, one
    SELECT id FROM products WHERE name = ? per item, and one INSERT INTO
    import_details per item — nothing else touches the database.
    """
    invoice, items = _require_clean_invoice(payload)

    cursor = db_conn.cursor()

    try:
        code = f"IMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        source = payload.get("source") or "n8n_vlm"
        raw_ocr_json = json.dumps(payload)
        supplier_name = payload.get("supplier_name")
        notes = payload.get("notes")
        warehouse_id = payload.get("warehouse_id")
        total_amount = float(invoice["total"])

        cursor.execute(
            """INSERT INTO import_transactions
               (code, supplier_name, total_amount, notes, status, source, raw_ocr_json, warehouse_id)
               VALUES (?, ?, ?, ?, 'pending_review', ?, ?, ?)""",
            (code, supplier_name, total_amount, notes, source, raw_ocr_json, warehouse_id),
        )
        import_id = cursor.lastrowid

        matched_count = 0
        unmatched_count = 0

        for item in items:
            name = item.get("name")
            qty = int(item.get("qty", 1))
            price = float(item.get("price", 0))
            is_reduced_vat = item.get("is_reduced_vat")
            total_price = qty * price

            product_id = None
            if name:
                cursor.execute("SELECT id FROM products WHERE name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    product_id = row[0]

            if product_id is not None:
                matched_count += 1
            else:
                unmatched_count += 1

            cursor.execute(
                """INSERT INTO import_details
                   (import_id, product_id, quantity, unit_price, total_price, raw_name, is_reduced_vat)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (import_id, product_id, qty, price, total_price, name, is_reduced_vat),
            )

        db_conn.commit()
        return {
            "id": import_id,
            "code": code,
            "status": "pending_review",
            "matched_count": matched_count,
            "unmatched_count": unmatched_count,
        }

    except ServiceValidationError:
        db_conn.rollback()
        raise
    except Exception as exc:
        db_conn.rollback()
        raise ServiceInvariantError(str(exc))
