"""Operations / analytics / reports / automations business logic — extracted from operations_routes."""
import json
from datetime import datetime

from core.extensions import db_manager


def _can_access_all(role):
    return role == 'admin'


def _owner_clause(user_id, role, prefix=''):
    if user_id is None or _can_access_all(role):
        return '', []
    column = f'{prefix}.created_by' if prefix else 'created_by'
    return f' AND {column} = ?', [user_id]


def get_dashboard_stats(user_id, warehouse_id=None):
    """Dashboard glance numbers. Scoped to a single warehouse/store when
    warehouse_id is given, so a retail chain owner sees that store's own
    revenue instead of the whole chain's combined total."""
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        today = datetime.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        if warehouse_id:
            c.execute('SELECT SUM(total_amount) AS total FROM export_transactions '
                      'WHERE created_at >= ? AND warehouse_id = ?', (start_of_month, warehouse_id))
        else:
            c.execute('SELECT SUM(total_amount) AS total FROM export_transactions WHERE created_at >= ?', (start_of_month,))
        revenue = c.fetchone()['total'] or 0
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        if warehouse_id:
            c.execute('SELECT COUNT(*) AS cnt FROM export_transactions '
                      'WHERE created_at >= ? AND warehouse_id = ?', (start_of_day, warehouse_id))
        else:
            c.execute('SELECT COUNT(*) AS cnt FROM export_transactions WHERE created_at >= ?', (start_of_day,))
        new_orders = c.fetchone()['cnt'] or 0
        c.execute('SELECT COUNT(*) AS cnt FROM workflows WHERE user_id = ?', (user_id,))
        active_projects = c.fetchone()['cnt'] or 0
        return {'revenue': revenue, 'new_orders': new_orders, 'active_projects': active_projects}
    finally:
        conn.close()


def get_report_stats(user_id=None, warehouse_id=None, role='user'):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        today = datetime.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
        owner_sql, owner_params = _owner_clause(user_id, role)
        warehouse_sql = ' AND warehouse_id = ?' if warehouse_id else ''
        warehouse_params = [warehouse_id] if warehouse_id else []
        c.execute(
            'SELECT SUM(total_amount) AS total FROM export_transactions WHERE created_at >= ?'
            + warehouse_sql + owner_sql,
            tuple([start_of_month] + warehouse_params + owner_params),
        )
        revenue = c.fetchone()['total'] or 0
        c.execute(
            'SELECT SUM(total_amount) AS total FROM import_transactions WHERE created_at >= ?'
            + warehouse_sql + owner_sql,
            tuple([start_of_month] + warehouse_params + owner_params),
        )
        expense = c.fetchone()['total'] or 0
        c.execute(
            'SELECT COUNT(*) AS cnt FROM scheduled_reports WHERE last_sent_at >= ?' + owner_sql,
            tuple([start_of_month] + owner_params),
        )
        reports_sent = c.fetchone()['cnt'] or 0
        return {'revenue': revenue, 'expense': expense,
                'profit': revenue - expense, 'reports_sent': reports_sent}
    finally:
        conn.close()


def get_scheduled_reports(user_id=None, role='user'):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        where = ''
        params = []
        if user_id is not None and not _can_access_all(role):
            where = ' WHERE created_by = ?'
            params.append(user_id)
        c.execute(
            'SELECT id, name, report_type, frequency, channel, recipients,'
            ' status, last_sent_at, created_by, created_at'
            ' FROM scheduled_reports' + where + ' ORDER BY created_at DESC',
            tuple(params),
        )
        return [
            {'id': r['id'], 'name': r['name'], 'report_type': r['report_type'],
             'frequency': r['frequency'], 'channel': r['channel'], 'recipients': r['recipients'],
             'status': r['status'], 'last_sent_at': r['last_sent_at']}
            for r in c.fetchall()
        ]
    finally:
        conn.close()


def create_scheduled_report(name, report_type, frequency, channel, recipients, created_by):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        c.execute(
            '''INSERT INTO scheduled_reports
               (name, report_type, frequency, channel, recipients, created_by)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (name, report_type, frequency, channel, recipients, created_by),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_scheduled_report(report_id, user_id=None, role='user'):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        query = 'DELETE FROM scheduled_reports WHERE id = ?'
        params = [report_id]
        if user_id is not None and not _can_access_all(role):
            query += ' AND created_by = ?'
            params.append(user_id)
        c.execute(query, tuple(params))
        if c.rowcount == 0:
            raise LookupError('Scheduled report not found')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_automations(user_id=None, role='user'):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        where = ''
        params = []
        if user_id is not None and not _can_access_all(role):
            where = ' WHERE created_by = ?'
            params.append(user_id)
        c.execute(
            'SELECT id, name, type, config, enabled, last_run, created_by, created_at'
            ' FROM se_automations' + where + ' ORDER BY created_at DESC',
            tuple(params),
        )
        return [
            {'id': r['id'], 'name': r['name'], 'type': r['type'],
             'config': json.loads(r['config']) if r['config'] else {},
             'status': 'active' if r['enabled'] else 'inactive', 'enabled': bool(r['enabled']),
             'last_run': r['last_run']}
            for r in c.fetchall()
        ]
    finally:
        conn.close()


def create_automation(name, auto_type, config, created_by):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    config_str = config if isinstance(config, str) else json.dumps(config)
    try:
        c.execute(
            'INSERT INTO se_automations (name, type, config, created_by) VALUES (?, ?, ?, ?)',
            (name, auto_type, config_str, created_by),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_automation(automation_id, data, user_id=None, role='user'):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        query = 'SELECT id FROM se_automations WHERE id = ?'
        params = [automation_id]
        if user_id is not None and not _can_access_all(role):
            query += ' AND created_by = ?'
            params.append(user_id)
        c.execute(query, tuple(params))
        if not c.fetchone():
            raise LookupError('Automation not found')
        if 'status' in data:
            c.execute('UPDATE se_automations SET enabled=? WHERE id=?',
                      (1 if data['status'] == 'active' else 0, automation_id))
        if 'name' in data:
            c.execute('UPDATE se_automations SET name=? WHERE id=?', (data['name'], automation_id))
        if 'config' in data:
            cfg = data['config']
            c.execute('UPDATE se_automations SET config=? WHERE id=?',
                      (cfg if isinstance(cfg, str) else json.dumps(cfg), automation_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_automation(automation_id, user_id=None, role='user'):
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        query = 'DELETE FROM se_automations WHERE id = ?'
        params = [automation_id]
        if user_id is not None and not _can_access_all(role):
            query += ' AND created_by = ?'
            params.append(user_id)
        c.execute(query, tuple(params))
        if c.rowcount == 0:
            raise LookupError('Automation not found')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
