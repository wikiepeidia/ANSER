"""User management business logic — extracted from admin_user_routes."""
from werkzeug.security import generate_password_hash

from core.extensions import db_manager


def get_all_users(role_filter=None):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        columns = db_manager.get_table_columns('users', cursor=c)
        has_first_name = 'first_name' in columns
        if has_first_name:
            if role_filter:
                c.execute(
                    'SELECT id, email, first_name, last_name, role, created_at '
                    'FROM users WHERE role = ? ORDER BY created_at DESC', (role_filter,)
                )
            else:
                c.execute(
                    'SELECT id, email, first_name, last_name, role, created_at '
                    'FROM users ORDER BY created_at DESC'
                )
            return [
                {'id': r[0], 'email': r[1], 'first_name': r[2] or '',
                 'last_name': r[3] or '', 'role': r[4], 'created_at': r[5]}
                for r in c.fetchall()
            ]
        else:
            if role_filter:
                c.execute(
                    'SELECT id, email, name, role, created_at '
                    'FROM users WHERE role = ? ORDER BY created_at DESC', (role_filter,)
                )
            else:
                c.execute(
                    'SELECT id, email, name, role, created_at FROM users ORDER BY created_at DESC'
                )
            return [
                {'id': r[0], 'email': r[1], 'name': r[2] or '', 'role': r[3], 'created_at': r[4]}
                for r in c.fetchall()
            ]
    finally:
        conn.close()


def get_users_for_manager(manager_id, role_filter=None):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        columns = db_manager.get_table_columns('users', cursor=c)
        has_first_name = 'first_name' in columns
        if has_first_name:
            query = ('SELECT id, email, first_name, last_name, role, created_at '
                     'FROM users WHERE manager_id = ?')
            params = [manager_id]
            if role_filter:
                query += ' AND role = ?'
                params.append(role_filter)
            query += ' ORDER BY created_at DESC'
            c.execute(query, tuple(params))
            return [
                {'id': r[0], 'email': r[1], 'first_name': r[2] or '',
                 'last_name': r[3] or '', 'role': r[4], 'created_at': r[5]}
                for r in c.fetchall()
            ]
        else:
            query = 'SELECT id, email, name, role, created_at FROM users WHERE manager_id = ?'
            params = [manager_id]
            if role_filter:
                query += ' AND role = ?'
                params.append(role_filter)
            query += ' ORDER BY created_at DESC'
            c.execute(query, tuple(params))
            return [
                {'id': r[0], 'email': r[1], 'name': r[2] or '', 'role': r[3], 'created_at': r[4]}
                for r in c.fetchall()
            ]
    finally:
        conn.close()


def delete_user(user_id):
    """Delete a regular (role='user') account. Raises LookupError/PermissionError."""
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        row = c.fetchone()
        if not row:
            raise LookupError('User not found')
        if row[0] != 'user':
            raise PermissionError('Can only delete regular users')
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def admin_delete_user(user_id):
    """Admin-level deletion (any role). Raises LookupError if not found."""
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        if c.rowcount == 0:
            raise LookupError('User not found')
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def reset_password(user_id, new_password):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        if not c.fetchone():
            raise LookupError('User not found')
        c.execute('UPDATE users SET password = ? WHERE id = ?',
                  (generate_password_hash(new_password), user_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def set_user_role(user_id, new_role, actor_id, actor_ip, action_label):
    """Change a user's role. Validates the target is not an admin."""
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        row = c.fetchone()
        if not row:
            raise LookupError('User not found')
        if row[0] == 'admin':
            raise PermissionError('Cannot change admin role')
        c.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        conn.commit()
        db_manager.log_activity(actor_id, action_label,
                                f'{action_label} user {user_id} to {new_role}', actor_ip)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
