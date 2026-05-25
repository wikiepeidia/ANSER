"""Customer CRUD — service layer extracted from main_routes."""
import sqlite3


def get_all_customers(conn):
    c = conn.cursor()
    c.execute(
        'SELECT id, code, name, phone, email, address, notes, created_by, created_at, updated_at'
        ' FROM customers ORDER BY created_at DESC'
    )
    rows = c.fetchall()
    return [
        {'id': r['id'], 'code': r['code'], 'name': r['name'], 'phone': r['phone'],
         'email': r['email'], 'address': r['address'], 'notes': r['notes'],
         'created_at': r['created_at']}
        for r in rows
    ]


def create_customer(conn, code, name, phone, email, address, notes, created_by):
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
    except Exception:
        conn.rollback()
        raise


def update_customer(conn, customer_id, name, phone, email, address, notes):
    c = conn.cursor()
    try:
        c.execute(
            '''UPDATE customers SET name=?, phone=?, email=?, address=?, notes=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (name, phone, email, address, notes, customer_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def delete_customer(conn, customer_id):
    c = conn.cursor()
    try:
        c.execute('DELETE FROM customers WHERE id=?', (customer_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
