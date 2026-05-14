"""Admin subscription business logic — extracted from admin_subscription_routes."""
import secrets
from datetime import datetime, timedelta

from core.config import Config
from core.extensions import db_manager


def get_all_subscriptions():
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute(
        '''SELECT s.id, s.user_id, s.subscription_type, s.amount, s.start_date, s.end_date,
                  s.status, s.auto_renew, u.name, u.email
           FROM manager_subscriptions s
           JOIN users u ON s.user_id = u.id
           ORDER BY s.end_date DESC'''
    )
    rows = c.fetchall()
    conn.close()
    return [
        {'id': r[0], 'user_id': r[1], 'subscription_type': r[2], 'amount': r[3],
         'start_date': r[4], 'end_date': r[5], 'status': r[6],
         'auto_renew': bool(r[7]) if r[7] is not None else False,
         'user_name': r[8], 'user_email': r[9]}
        for r in rows
    ]


def set_auto_renew(user_id, auto_renew):
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        columns = db_manager.get_table_columns('manager_subscriptions', cursor=c)
        if 'auto_renew' not in columns:
            c.execute('ALTER TABLE manager_subscriptions ADD COLUMN auto_renew INTEGER DEFAULT 0')
            conn.commit()
        c.execute(
            "UPDATE manager_subscriptions SET auto_renew=? WHERE user_id=? AND status='active'",
            (1 if auto_renew else 0, user_id),
        )
        conn.commit()
    finally:
        conn.close()


_PLANS = {
    'monthly':   {'days': 30,  'amount': 500000},
    'quarterly': {'days': 90,  'amount': 1200000},
    'yearly':    {'days': 365, 'amount': 4000000},
    'trial':     {'days': 30,  'amount': 0},
}


def extend_subscription(user_id, plan_type, payment_method, transaction_id=None):
    if plan_type not in _PLANS:
        raise ValueError('Invalid plan type')
    if not transaction_id:
        transaction_id = f'MANUAL-{secrets.token_hex(4).upper()}'
    plan = _PLANS[plan_type]
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT end_date FROM manager_subscriptions WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        now = datetime.now()
        start_date = now
        if row and row[0]:
            try:
                current_end = datetime.strptime(row[0], '%Y-%m-%d')
                if current_end > now:
                    start_date = current_end
            except ValueError:
                pass
        new_end = start_date + timedelta(days=plan['days'])
        new_end_str = new_end.strftime('%Y-%m-%d')
        if Config.USE_POSTGRES:
            c.execute(
                '''INSERT INTO manager_subscriptions
                   (user_id, subscription_type, amount, start_date, end_date, status, auto_renew)
                   VALUES (?, ?, ?, ?, ?, 'active', 0)
                   ON CONFLICT (user_id) DO UPDATE SET subscription_type=excluded.subscription_type,
                   amount=excluded.amount, start_date=excluded.start_date,
                   end_date=excluded.end_date, status='active' ''',
                (user_id, plan_type, plan['amount'], now.strftime('%Y-%m-%d'), new_end_str),
            )
        else:
            c.execute(
                '''INSERT OR REPLACE INTO manager_subscriptions
                   (user_id, subscription_type, amount, start_date, end_date, status, auto_renew)
                   VALUES (?, ?, ?, ?, ?, 'active', 0)''',
                (user_id, plan_type, plan['amount'], now.strftime('%Y-%m-%d'), new_end_str),
            )
        c.execute(
            '''INSERT INTO subscription_history
               (user_id, subscription_type, amount, payment_date, payment_method, transaction_id, status)
               VALUES (?, ?, ?, ?, ?, ?, 'Completed')''',
            (user_id, plan_type, plan['amount'], now.strftime('%Y-%m-%d %H:%M:%S'),
             payment_method, transaction_id),
        )
        conn.commit()
        return new_end_str
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_subscription_history():
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute(
        '''SELECT * FROM (
               SELECT h.id, h.user_id, h.subscription_type, h.amount,
                      h.payment_date, h.payment_method, h.transaction_id, h.status, u.name
               FROM subscription_history h JOIN users u ON h.user_id = u.id
               UNION ALL
               SELECT t.id, t.user_id, t.type, t.amount,
                      t.created_at, t.method, t.reference, t.status, u.name
               FROM wallet_transactions t JOIN users u ON t.user_id = u.id
               WHERE t.status = 'completed'
           ) ORDER BY payment_date DESC LIMIT 50'''
    )
    rows = c.fetchall()
    conn.close()
    return [
        {'id': r[0], 'user_id': r[1], 'subscription_type': r[2], 'amount': r[3],
         'payment_date': r[4], 'payment_method': r[5], 'transaction_id': r[6],
         'status': r[7], 'user_name': r[8]}
        for r in rows
    ]


def check_expired_subscriptions():
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute(
            "SELECT user_id FROM manager_subscriptions WHERE end_date < ? AND status = 'active'",
            (now,)
        )
        expired = c.fetchall()
        count = 0
        for (uid,) in expired:
            c.execute(
                "UPDATE manager_subscriptions SET status='expired', updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                (uid,)
            )
            c.execute('UPDATE users SET role=? WHERE id=?', ('user', uid))
            count += 1
        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
