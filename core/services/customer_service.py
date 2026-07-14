"""Customer CRUD — service layer extracted from main_routes."""
import sqlite3


def _can_access_all(role):
    return role == 'admin'


def get_all_customers(conn, user_id=None, role='user'):
    c = conn.cursor()
    query = (
        'SELECT id, code, name, phone, email, address, notes, created_by, created_at, updated_at'
        ' FROM customers'
    )
    params = []
    if user_id is not None and not _can_access_all(role):
        query += ' WHERE created_by = ?'
        params.append(user_id)
    query += ' ORDER BY created_at DESC'
    c.execute(query, tuple(params))
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


def update_customer(conn, customer_id, name, phone, email, address, notes, user_id=None, role='user'):
    c = conn.cursor()
    try:
        query = '''UPDATE customers SET name=?, phone=?, email=?, address=?, notes=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=?'''
        params = [name, phone, email, address, notes, customer_id]
        if user_id is not None and not _can_access_all(role):
            query += ' AND created_by=?'
            params.append(user_id)
        c.execute(query, tuple(params))
        if c.rowcount == 0:
            raise LookupError('Customer not found')
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def delete_customer(conn, customer_id, user_id=None, role='user'):
    c = conn.cursor()
    try:
        query = 'DELETE FROM customers WHERE id=?'
        params = [customer_id]
        if user_id is not None and not _can_access_all(role):
            query += ' AND created_by=?'
            params.append(user_id)
        c.execute(query, tuple(params))
        if c.rowcount == 0:
            raise LookupError('Customer not found')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
