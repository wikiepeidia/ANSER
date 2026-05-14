"""Product CRUD — service layer extracted from main_routes."""
import sqlite3

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
