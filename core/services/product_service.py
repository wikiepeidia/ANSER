"""Product CRUD — service layer extracted from main_routes."""
import sqlite3

import pandas as pd

from core.extensions import db_manager


def get_all_products():
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM products ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return [
        {'id': r[0], 'code': r[1], 'name': r[2], 'category': r[3],
         'unit': r[4], 'price': r[5], 'stock_quantity': r[6],
         'description': r[7], 'created_at': r[9]}
        for r in rows
    ]


def create_product(code, name, category, unit, price, stock_quantity, description, created_by):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute(
            '''INSERT INTO products (code, name, category, unit, price, stock_quantity, description, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (code, name, category, unit, price, stock_quantity, description, created_by),
        )
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, 'Product code already exists'
    finally:
        conn.close()


def update_product(product_id, name, category, unit, price, stock_quantity, description):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute(
            '''UPDATE products SET name=?, category=?, unit=?, price=?, stock_quantity=?,
               description=?, updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (name, category, unit, price, stock_quantity, description, product_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_product(product_id):
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM products WHERE id=?', (product_id,))
    conn.commit()
    conn.close()


def _get_next_sp_number(cursor):
    """Lấy số thứ tự tiếp theo cho mã SP (ví dụ: SP007 → trả về 8)."""
    cursor.execute("SELECT code FROM products WHERE code LIKE 'SP%'")
    numbers = []
    for (code,) in cursor.fetchall():
        try:
            numbers.append(int(code[2:]))
        except (ValueError, IndexError):
            pass
    return max(numbers, default=0) + 1


def import_products_from_excel(file_storage, created_by):
    """Upsert products from an uploaded Excel file.

    - Có code + tồn tại trong DB  → UPDATE
    - Có code + chưa có trong DB  → INSERT với code đó
    - Không có code               → tự động gán SP008, SP009... tiếp theo

    Returns dict: {inserted, updated, skipped, errors}
    """
    try:
        df = pd.read_excel(file_storage, engine='openpyxl')
    except Exception as e:
        raise ValueError(f'Không đọc được file Excel: {e}')

    df.columns = df.columns.str.lower().str.strip()

    if 'name' not in df.columns:
        raise ValueError("File thiếu cột bắt buộc: 'name'")

    result = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': []}

    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        next_sp_num = _get_next_sp_number(c)

        for i, row in df.iterrows():
            row_num = i + 2  # Excel row (header = row 1)

            name = str(row.get('name', '')).strip()
            if not name or name == 'nan':
                result['skipped'] += 1
                continue

            try:
                code = str(row['code']).strip() if 'code' in row and pd.notna(row['code']) else ''
                category = str(row['category']).strip() if 'category' in row and pd.notna(row['category']) else ''
                unit = str(row['unit']).strip() if 'unit' in row and pd.notna(row['unit']) else 'cái'
                price = float(row['price']) if 'price' in row and pd.notna(row['price']) else 0.0
                stock = int(float(row['stock_quantity'])) if 'stock_quantity' in row and pd.notna(row['stock_quantity']) else 0
                description = str(row['description']).strip() if 'description' in row and pd.notna(row['description']) else ''
            except (ValueError, TypeError) as e:
                result['errors'].append(f'Dòng {row_num}: Giá trị không hợp lệ — {e}')
                result['skipped'] += 1
                continue

            # Match theo NAME trong DB (bỏ qua code trong file Excel)
            c.execute('SELECT id, code FROM products WHERE LOWER(name) = LOWER(?)', (name,))
            existing = c.fetchone()

            if existing:
                existing_id, existing_code = existing
                if existing_code:
                    # Sản phẩm đã có code → UPDATE bình thường
                    c.execute(
                        '''UPDATE products SET category=?, unit=?, price=?,
                           stock_quantity=?, description=?, updated_at=CURRENT_TIMESTAMP
                           WHERE id=?''',
                        (category, unit, price, stock, description, existing_id),
                    )
                else:
                    # Có tên nhưng code NULL (rác) → gán SP code mới + UPDATE
                    auto_code = f'SP{next_sp_num:03d}'
                    next_sp_num += 1
                    c.execute(
                        '''UPDATE products SET code=?, category=?, unit=?, price=?,
                           stock_quantity=?, description=?, updated_at=CURRENT_TIMESTAMP
                           WHERE id=?''',
                        (auto_code, category, unit, price, stock, description, existing_id),
                    )
                result['updated'] += 1
            else:
                # Sản phẩm mới → tự động gán code SP tiếp theo
                auto_code = f'SP{next_sp_num:03d}'
                next_sp_num += 1
                c.execute(
                    '''INSERT INTO products (code, name, category, unit, price, stock_quantity, description, created_by)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                    (auto_code, name, category, unit, price, stock, description, created_by),
                )
                result['inserted'] += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return result
