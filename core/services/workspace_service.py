"""Workspace and item CRUD — extracted from workspace_routes."""
from core.extensions import db_manager


def get_workspace_items(workspace_id, user_id):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT id FROM workspaces WHERE id=? AND user_id=?', (workspace_id, user_id))
        if not c.fetchone():
            raise PermissionError('Workspace not found or access denied')
        c.execute(
            'SELECT id, workspace_id, title, description, type, status,'
            ' priority, assignee_id, due_date, created_at, updated_at'
            ' FROM items WHERE workspace_id=? ORDER BY created_at DESC',
            (workspace_id,),
        )
        return [
            {'id': r['id'], 'title': r['title'], 'description': r['description'],
             'type': r['type'], 'status': r['status'], 'priority': r['priority'],
             'created_at': r['created_at']}
            for r in c.fetchall()
        ]
    finally:
        conn.close()


def create_item(workspace_id, user_id, title, description, item_type, status, priority):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT id FROM workspaces WHERE id=? AND user_id=?', (workspace_id, user_id))
        if not c.fetchone():
            raise PermissionError('Workspace not found or access denied')
        c.execute(
            '''INSERT INTO items (workspace_id, title, description, type, status, priority, assignee_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (workspace_id, title, description, item_type, status, priority, user_id),
        )
        conn.commit()
        return c.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_item(item_id, user_id, title, description, status, priority):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        c.execute(
            '''UPDATE items SET title=?, description=?, status=?, priority=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=? AND assignee_id=?''',
            (title, description, status, priority, item_id, user_id),
        )
        conn.commit()
        if c.rowcount == 0:
            raise LookupError('Item not found or unauthorized')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_item(item_id, user_id):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM items WHERE id=? AND assignee_id=?', (item_id, user_id))
        conn.commit()
        if c.rowcount == 0:
            raise LookupError('Item not found or unauthorized')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_workspace(user_id, name, ws_type, description):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        c.execute(
            'INSERT INTO workspaces (user_id, name, type, description) VALUES (?, ?, ?, ?)',
            (user_id, name, ws_type, description),
        )
        conn.commit()
        return c.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
