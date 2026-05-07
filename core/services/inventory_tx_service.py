"""Inventory import/export transaction service functions."""

import secrets
from datetime import datetime

from .service_errors import ServiceInvariantError, ServiceValidationError


def _require_payload(payload):
    if not isinstance(payload, dict):
        raise ServiceValidationError("payload must be a dictionary")


def _require_user(user_id):
    if user_id is None:
        raise ServiceValidationError("user_id is required")


def _require_items(payload, label):
    items = payload.get("items", [])
    if not items:
        raise ServiceValidationError(f"No items in {label}")
    return items


def create_import_transaction(db_conn, user_id, payload):
    """Create import transaction, details, and stock updates in one transaction."""
    _require_user(user_id)
    _require_payload(payload)
    items = _require_items(payload, "import")

    supplier_name = payload.get("supplier_name")
    notes = payload.get("notes")
    cursor = db_conn.cursor()

    try:
        code = f"IMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        total_amount = sum(float(item["quantity"]) * float(item["unit_price"]) for item in items)

        cursor.execute(
            """INSERT INTO import_transactions
               (code, supplier_name, total_amount, notes, created_by)
               VALUES (?, ?, ?, ?, ?)""",
            (code, supplier_name, total_amount, notes, user_id),
        )
        import_id = cursor.lastrowid

        for item in items:
            product_id = item.get("product_id")
            product_name = item.get("product_name")
            quantity = int(item["quantity"])
            unit_price = float(item["unit_price"])
            total_price = quantity * unit_price

            if not product_id and product_name:
                cursor.execute("SELECT id FROM products WHERE name = ?", (product_name,))
                row = cursor.fetchone()
                if row:
                    product_id = row[0]
                else:
                    p_code = f"P-{datetime.now().strftime('%H%M%S')}-{secrets.token_hex(2).upper()}"
                    cursor.execute(
                        """INSERT INTO products (code, name, price, stock_quantity, created_by)
                           VALUES (?, ?, ?, 0, ?)""",
                        (p_code, product_name, unit_price, user_id),
                    )
                    product_id = cursor.lastrowid

            if product_id:
                cursor.execute(
                    """INSERT INTO import_details
                       (import_id, product_id, quantity, unit_price, total_price)
                       VALUES (?, ?, ?, ?, ?)""",
                    (import_id, product_id, quantity, unit_price, total_price),
                )
                cursor.execute(
                    "UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                    (quantity, product_id),
                )

        db_conn.commit()
        return {"id": import_id, "message": "Import created successfully"}

    except ServiceValidationError:
        db_conn.rollback()
        raise
    except Exception as exc:
        db_conn.rollback()
        raise ServiceInvariantError(str(exc))


def get_import_transaction_details(db_conn, import_id):
    """Fetch import transaction and item detail rows."""
    cursor = db_conn.cursor()

    try:
        cursor.execute("SELECT * FROM import_transactions WHERE id = ?", (import_id,))
        row = cursor.fetchone()
        if not row:
            return None

        transaction = {
            "id": row[0],
            "code": row[1],
            "supplier_name": row[2],
            "total_amount": row[3],
            "notes": row[4],
            "status": row[5],
            "created_at": row[7],
        }

        cursor.execute(
            """SELECT d.*, p.name as product_name, p.code as product_code
               FROM import_details d
               JOIN products p ON d.product_id = p.id
               WHERE d.import_id = ?""",
            (import_id,),
        )

        details = []
        for d_row in cursor.fetchall():
            details.append(
                {
                    "id": d_row[0],
                    "product_id": d_row[2],
                    "quantity": d_row[3],
                    "unit_price": d_row[4],
                    "total_price": d_row[5],
                    "product_name": d_row[6],
                    "product_code": d_row[7],
                }
            )

        return {"transaction": transaction, "details": details}

    except Exception as exc:
        raise ServiceInvariantError(str(exc))


def create_export_transaction(db_conn, user_id, payload, automation_engine=None):
    """Create export transaction with stock checks and rollback on violations."""
    _require_user(user_id)
    _require_payload(payload)
    items = _require_items(payload, "export")

    customer_id = payload.get("customer_id")
    notes = payload.get("notes")
    cursor = db_conn.cursor()
    updated_products = []

    try:
        code = f"EXP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        total_amount = sum(float(item["quantity"]) * float(item["unit_price"]) for item in items)

        cursor.execute(
            """INSERT INTO export_transactions
               (code, customer_id, total_amount, notes, created_by)
               VALUES (?, ?, ?, ?, ?)""",
            (code, customer_id, total_amount, notes, user_id),
        )
        export_id = cursor.lastrowid

        for item in items:
            product_id = item["product_id"]
            quantity = int(item["quantity"])
            unit_price = float(item["unit_price"])
            total_price = quantity * unit_price

            cursor.execute("SELECT stock_quantity FROM products WHERE id = ?", (product_id,))
            stock_row = cursor.fetchone()
            if not stock_row:
                raise ServiceValidationError(f"Product not found for product ID {product_id}")

            current_stock = stock_row[0]
            if current_stock < quantity:
                raise ServiceValidationError(f"Insufficient stock for product ID {product_id}")

            cursor.execute(
                """INSERT INTO export_details
                   (export_id, product_id, quantity, unit_price, total_price)
                   VALUES (?, ?, ?, ?, ?)""",
                (export_id, product_id, quantity, unit_price, total_price),
            )

            new_stock = current_stock - quantity
            cursor.execute(
                "UPDATE products SET stock_quantity = ? WHERE id = ?",
                (new_stock, product_id),
            )
            updated_products.append((product_id, new_stock))

        db_conn.commit()

        if automation_engine is not None:
            for product_id, stock_quantity in updated_products:
                try:
                    automation_engine.check_low_stock(product_id, stock_quantity)
                except Exception:
                    pass

        return {"id": export_id, "message": "Export created successfully"}

    except ServiceValidationError:
        db_conn.rollback()
        raise
    except Exception as exc:
        db_conn.rollback()
        raise ServiceInvariantError(str(exc))


def get_export_transaction_details(db_conn, export_id):
    """Fetch export transaction and item detail rows."""
    cursor = db_conn.cursor()

    try:
        cursor.execute(
            """SELECT e.*, c.name as customer_name, c.phone as customer_phone
               FROM export_transactions e
               LEFT JOIN customers c ON e.customer_id = c.id
               WHERE e.id = ?""",
            (export_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        transaction = {
            "id": row[0],
            "code": row[1],
            "customer_id": row[2],
            "total_amount": row[3],
            "notes": row[4],
            "status": row[5],
            "created_at": row[7],
            "customer_name": row[8] if len(row) > 8 else "",
            "customer_phone": row[9] if len(row) > 9 else "",
        }

        cursor.execute(
            """SELECT d.*, p.name as product_name, p.code as product_code
               FROM export_details d
               JOIN products p ON d.product_id = p.id
               WHERE d.export_id = ?""",
            (export_id,),
        )

        details = []
        for d_row in cursor.fetchall():
            details.append(
                {
                    "id": d_row[0],
                    "product_id": d_row[2],
                    "quantity": d_row[3],
                    "unit_price": d_row[4],
                    "total_price": d_row[5],
                    "product_name": d_row[6],
                    "product_code": d_row[7],
                }
            )

        return {"transaction": transaction, "details": details}

    except Exception as exc:
        raise ServiceInvariantError(str(exc))
