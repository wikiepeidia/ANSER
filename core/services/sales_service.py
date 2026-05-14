"""Sales business logic — extracted from sales_routes."""
import json

from core.extensions import db_manager
from core.helpers import format_display_datetime


def create_sale(user_id, total_amount, amount_given, change_amount, items,
                payment_method, workspace_id, category):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        items_json = items if isinstance(items, str) else json.dumps(items)
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
    finally:
        conn.close()


def get_sales_history(user_id, search_query='', limit=10):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        query = ('SELECT id, created_at, total_amount, payment_method, items '
                 'FROM sales WHERE user_id = ?')
        params = [user_id]
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
                raw = row[4]
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
                'id': row[0],
                'date': format_display_datetime(row[1]) or str(row[1]),
                'amount': row[2],
                'payment_method': row[3] or 'Cash',
                'item_count': item_count,
                'items': items,
            })
        return history
    finally:
        conn.close()


def delete_sale(sale_id):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM sales WHERE id = ?', (sale_id,))
        conn.commit()
        if c.rowcount == 0:
            raise LookupError('Sale not found')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
