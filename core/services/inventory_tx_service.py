"""Các hàm service cho giao dịch nhập/xuất kho."""

import secrets
from datetime import datetime

from .service_errors import ServiceInvariantError, ServiceValidationError


def _require_payload(payload):
    if not isinstance(payload, dict):
        raise ServiceValidationError("payload phải là một dictionary")


def _require_user(user_id):
    if user_id is None:
        raise ServiceValidationError("user_id là bắt buộc")


def _require_items(payload, label):
    items = payload.get("items", [])
    if not items:
        raise ServiceValidationError(f"Không có mục nào trong {label}")
    return items


def get_warehouse_stock(cursor, warehouse_id, product_id):
    """Tồn kho của 1 sản phẩm tại 1 kho cụ thể (0 nếu chưa có dòng nào)."""
    if not warehouse_id:
        return None
    cursor.execute(
        "SELECT stock_quantity FROM warehouse_stock WHERE warehouse_id = ? AND product_id = ?",
        (warehouse_id, product_id),
    )
    row = cursor.fetchone()
    return row["stock_quantity"] if row else 0


def _adjust_warehouse_stock(cursor, warehouse_id, product_id, delta):
    """Cộng/trừ tồn kho của 1 sản phẩm tại 1 kho, tạo dòng nếu chưa có."""
    current = get_warehouse_stock(cursor, warehouse_id, product_id) or 0
    new_qty = current + delta
    cursor.execute(
        """INSERT INTO warehouse_stock (warehouse_id, product_id, stock_quantity, updated_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(warehouse_id, product_id)
           DO UPDATE SET stock_quantity = excluded.stock_quantity, updated_at = CURRENT_TIMESTAMP""",
        (warehouse_id, product_id, new_qty),
    )
    return new_qty


def _sync_product_total_stock(cursor, product_id):
    """products.stock_quantity = tổng tồn kho của sản phẩm này trên tất cả các kho.

    Giữ cột này như một tổng hợp toàn hệ thống (cho các chỗ đọc chưa nhận
    thức được khái niệm kho, vd cảnh báo tồn kho thấp cũ), thay vì xóa cột.
    """
    cursor.execute(
        "UPDATE products SET stock_quantity = "
        "(SELECT COALESCE(SUM(stock_quantity), 0) FROM warehouse_stock WHERE product_id = ?) "
        "WHERE id = ?",
        (product_id, product_id),
    )


def create_import_transaction(db_conn, user_id, payload, warehouse_id=None):
    """Tạo giao dịch nhập, chi tiết và cập nhật tồn kho trong một giao dịch.

    warehouse_id: kho đang thao tác (None = tương thích ngược, chỉ cập nhật
    products.stock_quantity như trước, không ghi vào warehouse_stock).
    """
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
               (code, supplier_name, total_amount, notes, created_by, warehouse_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (code, supplier_name, total_amount, notes, user_id, warehouse_id),
        )
        import_id = cursor.lastrowid

        products_updated = 0
        products_created = 0

        for item in items:
            product_id = item.get("product_id")
            product_code = item.get("product_code")
            product_name = item.get("product_name")
            quantity = int(item["quantity"])
            unit_price = float(item["unit_price"])
            total_price = quantity * unit_price

            if not product_id:
                # Look up by code first, then by name
                if product_code:
                    cursor.execute("SELECT id FROM products WHERE code = ?", (product_code,))
                    row = cursor.fetchone()
                    if row:
                        product_id = row[0]
                        products_updated += 1

                if not product_id and product_name:
                    cursor.execute("SELECT id FROM products WHERE name = ?", (product_name,))
                    row = cursor.fetchone()
                    if row:
                        product_id = row[0]
                        products_updated += 1
                    else:
                        p_code = product_code or f"P-{datetime.now().strftime('%H%M%S')}-{secrets.token_hex(2).upper()}"
                        cursor.execute(
                            """INSERT INTO products (code, name, price, stock_quantity, created_by)
                               VALUES (?, ?, ?, 0, ?)""",
                            (p_code, product_name, unit_price, user_id),
                        )
                        product_id = cursor.lastrowid
                        products_created += 1
            else:
                products_updated += 1

            if product_id:
                cursor.execute(
                    """INSERT INTO import_details
                       (import_id, product_id, quantity, unit_price, total_price)
                       VALUES (?, ?, ?, ?, ?)""",
                    (import_id, product_id, quantity, unit_price, total_price),
                )
                if warehouse_id:
                    _adjust_warehouse_stock(cursor, warehouse_id, product_id, quantity)
                    _sync_product_total_stock(cursor, product_id)
                else:
                    cursor.execute(
                        "UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?",
                        (quantity, product_id),
                    )

        db_conn.commit()
        return {
            "id": import_id,
            "message": "Import created successfully",
            "products_updated": products_updated,
            "products_created": products_created,
        }

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
        cursor.execute(
            'SELECT id, code, supplier_name, total_amount, notes, status, created_by, created_at'
            ' FROM import_transactions WHERE id = ?',
            (import_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        transaction = {
            "id": row['id'],
            "code": row['code'],
            "supplier_name": row['supplier_name'],
            "total_amount": row['total_amount'],
            "notes": row['notes'],
            "status": row['status'],
            "created_at": row['created_at'],
        }

        cursor.execute(
            'SELECT d.id, d.import_id, d.product_id, d.quantity, d.unit_price, d.total_price,'
            ' p.name AS product_name, p.code AS product_code'
            ' FROM import_details d'
            ' JOIN products p ON d.product_id = p.id'
            ' WHERE d.import_id = ?',
            (import_id,),
        )

        details = []
        for d_row in cursor.fetchall():
            details.append(
                {
                    "id": d_row['id'],
                    "product_id": d_row['product_id'],
                    "quantity": d_row['quantity'],
                    "unit_price": d_row['unit_price'],
                    "total_price": d_row['total_price'],
                    "product_name": d_row['product_name'],
                    "product_code": d_row['product_code'],
                }
            )

        return {"transaction": transaction, "details": details}

    except Exception as exc:
        raise ServiceInvariantError(str(exc))


def create_export_transaction(db_conn, user_id, payload, automation_engine=None, warehouse_id=None):
    """Create export transaction with stock checks and rollback on violations.

    warehouse_id: kho đang thao tác (None = tương thích ngược, kiểm tra/trừ
    thẳng products.stock_quantity như trước, không ghi vào warehouse_stock).
    """
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
               (code, customer_id, total_amount, notes, created_by, warehouse_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (code, customer_id, total_amount, notes, user_id, warehouse_id),
        )
        export_id = cursor.lastrowid

        for item in items:
            product_id = item["product_id"]
            quantity = int(item["quantity"])
            unit_price = float(item["unit_price"])
            total_price = quantity * unit_price

            if warehouse_id:
                current_stock = get_warehouse_stock(cursor, warehouse_id, product_id)
                cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
                if not cursor.fetchone():
                    raise ServiceValidationError(f"Product not found for product ID {product_id}")
            else:
                cursor.execute("SELECT stock_quantity FROM products WHERE id = ?", (product_id,))
                stock_row = cursor.fetchone()
                if not stock_row:
                    raise ServiceValidationError(f"Product not found for product ID {product_id}")
                current_stock = stock_row['stock_quantity']

            if current_stock < quantity:
                raise ServiceValidationError(f"Insufficient stock for product ID {product_id}")

            cursor.execute(
                """INSERT INTO export_details
                   (export_id, product_id, quantity, unit_price, total_price)
                   VALUES (?, ?, ?, ?, ?)""",
                (export_id, product_id, quantity, unit_price, total_price),
            )

            if warehouse_id:
                new_stock = _adjust_warehouse_stock(cursor, warehouse_id, product_id, -quantity)
                _sync_product_total_stock(cursor, product_id)
            else:
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
            'SELECT e.id, e.code, e.customer_id, e.total_amount, e.notes, e.status,'
            ' e.created_by, e.created_at,'
            ' c.name AS customer_name, c.phone AS customer_phone'
            ' FROM export_transactions e'
            ' LEFT JOIN customers c ON e.customer_id = c.id'
            ' WHERE e.id = ?',
            (export_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        transaction = {
            "id": row['id'],
            "code": row['code'],
            "customer_id": row['customer_id'],
            "total_amount": row['total_amount'],
            "notes": row['notes'],
            "status": row['status'],
            "created_at": row['created_at'],
            "customer_name": row['customer_name'] or "",
            "customer_phone": row['customer_phone'] or "",
        }

        cursor.execute(
            'SELECT d.id, d.export_id, d.product_id, d.quantity, d.unit_price, d.total_price,'
            ' p.name AS product_name, p.code AS product_code'
            ' FROM export_details d'
            ' JOIN products p ON d.product_id = p.id'
            ' WHERE d.export_id = ?',
            (export_id,),
        )

        details = []
        for d_row in cursor.fetchall():
            details.append(
                {
                    "id": d_row['id'],
                    "product_id": d_row['product_id'],
                    "quantity": d_row['quantity'],
                    "unit_price": d_row['unit_price'],
                    "total_price": d_row['total_price'],
                    "product_name": d_row['product_name'],
                    "product_code": d_row['product_code'],
                }
            )

        return {"transaction": transaction, "details": details}

    except Exception as exc:
        raise ServiceInvariantError(str(exc))
