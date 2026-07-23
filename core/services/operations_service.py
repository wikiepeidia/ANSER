"""Operations / analytics / reports / automations business logic — extracted from operations_routes."""
import json
import uuid
from datetime import datetime, timedelta

from core.extensions import db_manager
from core.logger import get_logger

logger = get_logger(__name__)


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

        # Today's actual POS revenue — from `sales` (the real checkout table,
        # same source daily_sales_report's email reads via
        # /api/n8n/internal/daily-sales), not `export_transactions` above
        # (a different, warehouse-transfer-style revenue figure). Staff need
        # this one: "how much did we sell today," not month-to-date exports.
        if warehouse_id:
            c.execute("SELECT COUNT(*) AS cnt, COALESCE(SUM(total_amount), 0) AS total FROM sales "
                      "WHERE warehouse_id = ? AND created_at >= ?", (warehouse_id, start_of_day))
        else:
            c.execute("SELECT COUNT(*) AS cnt, COALESCE(SUM(total_amount), 0) AS total FROM sales "
                      "WHERE created_at >= ?", (start_of_day,))
        row = c.fetchone()
        today_revenue = float(row['total'] or 0)
        today_sales_count = row['cnt'] or 0

        return {'revenue': revenue, 'new_orders': new_orders, 'active_projects': active_projects,
                'today_revenue': today_revenue, 'today_sales_count': today_sales_count}
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
    """id/status are set explicitly rather than left to column defaults —
    production's scheduled_reports table predates Alembic and (until
    migration 006) had neither, so every row created here ended up with
    id=NULL, status=NULL: undeletable and invisible to the scheduler."""
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        report_id = uuid.uuid4().hex[:12]
        c.execute(
            '''INSERT INTO scheduled_reports
               (id, name, report_type, frequency, channel, recipients, status, created_by)
               VALUES (?, ?, ?, ?, ?, ?, 'active', ?)''',
            (report_id, name, report_type, frequency, channel, recipients, created_by),
        )
        conn.commit()
        return report_id
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


# ── Scheduled reports execution ──────────────────────────────────────────────
# Actually sends what /se/reports's "Lên lịch báo cáo" form creates — that
# form used to only INSERT into scheduled_reports and stop there (no
# process ever read the table back out). run_due_scheduled_reports() is
# that missing process; core/report_scheduler.py calls it periodically.

_FREQUENCY_DELTA = {
    'daily': timedelta(days=1),
    'weekly': timedelta(days=7),
    'monthly': timedelta(days=30),
}


def _parse_ts(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)[:26]
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _is_due(frequency, last_sent_at):
    last = _parse_ts(last_sent_at)
    if last is None:
        return True
    delta = _FREQUENCY_DELTA.get(frequency, timedelta(days=1))
    return datetime.now() >= last + delta


def _build_report_email(conn, report_type):
    """Return (subject, html) for a known report_type, or (None, None)."""
    c = conn.cursor()
    since = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')

    if report_type == 'revenue_expense':
        c.execute('SELECT COALESCE(SUM(total_amount), 0) AS total FROM export_transactions WHERE created_at >= ?', (since,))
        revenue = float(c.fetchone()['total'] or 0)
        c.execute('SELECT COALESCE(SUM(total_amount), 0) AS total FROM import_transactions WHERE created_at >= ?', (since,))
        expense = float(c.fetchone()['total'] or 0)
        fmt = lambda n: f'{n:,.0f}'.replace(',', '.')
        html = (f'<h2>Tóm tắt doanh thu & chi phí (24h qua)</h2>'
                f'<p>Doanh thu: <b>{fmt(revenue)} đ</b></p>'
                f'<p>Chi phí: <b>{fmt(expense)} đ</b></p>'
                f'<p>Lợi nhuận: <b>{fmt(revenue - expense)} đ</b></p>')
        return 'Báo cáo doanh thu & chi phí', html

    if report_type == 'inventory':
        c.execute('SELECT name, code, stock_quantity FROM products WHERE stock_quantity < 10 ORDER BY stock_quantity ASC LIMIT 20')
        rows = c.fetchall()
        items = ''.join(
            f"<tr><td>{r['name']}</td><td>{r['code']}</td><td>{r['stock_quantity']}</td></tr>" for r in rows
        ) or '<tr><td colspan="3">Không có sản phẩm nào dưới ngưỡng 10</td></tr>'
        html = (f'<h2>Tình trạng tồn kho</h2>'
                f'<table border="1" cellpadding="6" cellspacing="0">'
                f'<tr><th>Sản phẩm</th><th>Mã</th><th>Còn lại</th></tr>{items}</table>')
        return 'Báo cáo tồn kho', html

    if report_type == 'customer_activity':
        c.execute('SELECT COUNT(*) AS cnt FROM customers WHERE created_at >= ?', (since,))
        new_customers = c.fetchone()['cnt'] or 0
        html = f'<h2>Hoạt động khách hàng</h2><p>Khách hàng mới (24h qua): <b>{new_customers}</b></p>'
        return 'Báo cáo hoạt động khách hàng', html

    return None, None


def run_due_scheduled_reports():
    """Send every scheduled_reports row that's due. Only channel='email' is
    implemented — 'slack'/'download' rows are logged and left un-sent
    (last_sent_at untouched) rather than silently marked as delivered."""
    from core.smtp_mailer import send_smtp_email

    conn = db_manager.get_business_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, name, report_type, frequency, channel, recipients, last_sent_at "
        "FROM scheduled_reports WHERE status = 'active'"
    )
    rows = c.fetchall()

    sent = 0
    for r in rows:
        if not _is_due(r['frequency'], r['last_sent_at']):
            continue
        if r['channel'] != 'email' or not r['recipients']:
            logger.info('[reports] Skipping "%s": channel=%s not implemented or no recipients',
                        r['name'], r['channel'])
            continue
        subject, html = _build_report_email(conn, r['report_type'])
        if not subject:
            logger.warning('[reports] Unknown report_type "%s" for report id=%s', r['report_type'], r['id'])
            continue
        if send_smtp_email(r['recipients'], f'{subject} — {r["name"]}', html):
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute('UPDATE scheduled_reports SET last_sent_at = ? WHERE id = ?', (now, r['id']))
            conn.commit()
            sent += 1
            logger.info('[reports] Sent "%s" to %s', r['name'], r['recipients'])
    conn.close()
    return sent
