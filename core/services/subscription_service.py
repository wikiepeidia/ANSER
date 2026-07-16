"""Admin subscription business logic — extracted from admin_subscription_routes.

manager_subscriptions/subscription_history/wallet_transactions live in the
business DB; `users` lives in the separate shared auth DB. Any function that
used to JOIN the two in one SQL query now does two queries and merges in
Python (Postgres doesn't support cross-database JOINs, even within the same
Neon project).
"""
import secrets
from datetime import datetime, timedelta

from core.config import Config
from core.extensions import db_manager


def _users_by_id(auth_conn, user_ids):
    if not user_ids:
        return {}
    c = auth_conn.cursor()
    placeholders = ', '.join(['?'] * len(user_ids))
    c.execute(f'SELECT id, name, email FROM users WHERE id IN ({placeholders})', list(user_ids))
    return {u['id']: u for u in c.fetchall()}


def get_all_subscriptions():
    conn = db_manager.get_business_connection()
    auth_conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute(
        '''SELECT id, user_id, subscription_type, amount, start_date, end_date, status, auto_renew
           FROM manager_subscriptions ORDER BY end_date DESC'''
    )
    rows = c.fetchall()
    conn.close()

    users = _users_by_id(auth_conn, {r['user_id'] for r in rows})
    auth_conn.close()

    return [
        {'id': r['id'], 'user_id': r['user_id'], 'subscription_type': r['subscription_type'],
         'amount': r['amount'], 'start_date': r['start_date'], 'end_date': r['end_date'],
         'status': r['status'],
         'auto_renew': bool(r['auto_renew']) if r['auto_renew'] is not None else False,
         'user_name': users[r['user_id']]['name'] if r['user_id'] in users else None,
         'user_email': users[r['user_id']]['email'] if r['user_id'] in users else None}
        for r in rows
    ]


def set_auto_renew(user_id, auto_renew):
    conn = db_manager.get_business_connection()
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
    conn = db_manager.get_business_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT end_date FROM manager_subscriptions WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        now = datetime.now()
        start_date = now
        if row and row['end_date']:
            try:
                current_end = datetime.strptime(row['end_date'], '%Y-%m-%d')
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
    conn = db_manager.get_business_connection()
    auth_conn = db_manager.get_connection()
    c = conn.cursor()

    c.execute(
        '''SELECT id, user_id, subscription_type, amount, payment_date, payment_method,
                  transaction_id, status
           FROM subscription_history ORDER BY payment_date DESC LIMIT 50'''
    )
    sub_rows = [
        {'id': r['id'], 'user_id': r['user_id'], 'subscription_type': r['subscription_type'],
         'amount': r['amount'], 'payment_date': r['payment_date'],
         'payment_method': r['payment_method'], 'transaction_id': r['transaction_id'],
         'status': r['status']}
        for r in c.fetchall()
    ]

    c.execute(
        '''SELECT id, user_id, type AS subscription_type, amount, created_at AS payment_date,
                  method AS payment_method, reference AS transaction_id, status
           FROM wallet_transactions WHERE status = 'completed'
           ORDER BY created_at DESC LIMIT 50'''
    )
    wallet_rows = [
        {'id': r['id'], 'user_id': r['user_id'], 'subscription_type': r['subscription_type'],
         'amount': r['amount'], 'payment_date': r['payment_date'],
         'payment_method': r['payment_method'], 'transaction_id': r['transaction_id'],
         'status': r['status']}
        for r in c.fetchall()
    ]
    conn.close()

    combined = sub_rows + wallet_rows
    combined.sort(key=lambda r: r['payment_date'] or '', reverse=True)
    combined = combined[:50]

    users = _users_by_id(auth_conn, {r['user_id'] for r in combined})
    auth_conn.close()

    for r in combined:
        r['user_name'] = users[r['user_id']]['name'] if r['user_id'] in users else None
    return combined


def check_expired_subscriptions():
    """Downgrade the auth-DB role FIRST, then mark expired in the business
    DB second — the opposite order from a payment flow. If the business-DB
    write failed after the role was already downgraded, re-running this is
    harmless (still status='active', role update is idempotent). If it were
    the other way around and only the role update failed, the row would no
    longer match `status='active'` and would never be retried, leaving the
    user stuck with a manager role forever."""
    conn = db_manager.get_business_connection()
    auth_conn = db_manager.get_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute(
        "SELECT user_id FROM manager_subscriptions WHERE end_date < ? AND status = 'active'",
        (now,)
    )
    expired = c.fetchall()

    count = 0
    ac = auth_conn.cursor()
    for row in expired:
        uid = row['user_id']
        try:
            ac.execute('UPDATE users SET role=? WHERE id=?', ('user', uid))
            auth_conn.commit()
        except Exception:
            auth_conn.rollback()
            raise
        c.execute(
            "UPDATE manager_subscriptions SET status='expired', updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
            (uid,)
        )
        conn.commit()
        count += 1

    conn.close()
    auth_conn.close()
    return count
