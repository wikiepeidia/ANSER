"""Customer CRUD — service layer extracted from main_routes."""
import sqlite3

from core.extensions import db_manager


def get_all_customers():
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM customers ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return [
        {'id': r[0], 'code': r[1], 'name': r[2], 'phone': r[3],
         'email': r[4], 'address': r[5], 'notes': r[6], 'created_at': r[8]}
        for r in rows
    ]


def create_customer(code, name, phone, email, address, notes, created_by):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute(
            '''INSERT INTO customers (code, name, phone, email, address, notes, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (code, name, phone, email, address, notes, created_by),
        )
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, 'Customer code already exists'
    finally:
        conn.close()


def update_customer(customer_id, name, phone, email, address, notes):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute(
            '''UPDATE customers SET name=?, phone=?, email=?, address=?, notes=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (name, phone, email, address, notes, customer_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_customer(customer_id):
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM customers WHERE id=?', (customer_id,))
    conn.commit()
    conn.close()
