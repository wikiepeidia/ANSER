"""Sales business logic — extracted from sales_routes."""
import json

from core.helpers import format_display_datetime


def _has_column(cursor, table, column):
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        return any(row['name'] == column for row in cursor.fetchall())
    except Exception:
        return True


def create_sale(conn, user_id, total_amount, amount_given, change_amount, items,
                payment_method, workspace_id, category, warehouse_id=None):
    c = conn.cursor()
    try:
        items_json = items if isinstance(items, str) else json.dumps(items)
        if _has_column(c, 'sales', 'warehouse_id'):
            c.execute(
                '''INSERT INTO sales (user_id, total_amount, amount_given, change_amount, items,
                   payment_method, workspace_id, category, warehouse_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, total_amount, amount_given, change_amount, items_json,
                 payment_method, workspace_id, category, warehouse_id),
            )
        else:
            c.execute(
                '''INSERT INTO sales (user_id, total_amount, amount_given, change_amount, items,
                   payment_method, workspace_id, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, total_amount, amount_given, change_amount, items_json,
                 payment_method, workspace_id, category),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_sales_history(conn, user_id, search_query='', limit=10, warehouse_id=None):
    c = conn.cursor()
    query = ('SELECT id, created_at, total_amount, payment_method, items '
             'FROM sales WHERE user_id = ?')
    params = [user_id]
    if warehouse_id and _has_column(c, 'sales', 'warehouse_id'):
        query += ' AND warehouse_id = ?'
        params.append(warehouse_id)
    if search_query:
        if search_query.isdigit():
            query += ' AND CAST(id AS TEXT) LIKE ?'
            params.append(f'%{search_query}%')
        else:
            query += ' AND LOWER(payment_method) LIKE ?'
            params.append(f'%{search_query.lower()}%')
    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)
    c.execute(query, tuple(params))
    history = []
    for row in c.fetchall():
        try:
            raw = row['items']
            if not raw:
                items = []
            elif isinstance(raw, str):
                items = json.loads(raw)
            elif isinstance(raw, (dict, list)):
                items = raw
            else:
                items = []
            item_count = (
                sum(int(item.get('qty', 0)) for item in items if isinstance(item, dict))
                if isinstance(items, list) else 0
            )
        except Exception:
            items = []
            item_count = 0
        history.append({
            'id': row['id'],
            'date': format_display_datetime(row['created_at']) or str(row['created_at']),
            'amount': row['total_amount'],
            'payment_method': row['payment_method'] or 'Cash',
            'item_count': item_count,
            'items': items,
        })
    return history


def delete_sale(conn, sale_id, user_id=None):
    c = conn.cursor()
    try:
        if user_id is None:
            c.execute('DELETE FROM sales WHERE id = ?', (sale_id,))
        else:
            c.execute('DELETE FROM sales WHERE id = ? AND user_id = ?', (sale_id, user_id))
        conn.commit()
        if c.rowcount == 0:
            raise LookupError('Sale not found')
    except Exception:
        conn.rollback()
        raise
