"""Wallet business logic — extracted from wallet_routes."""
import json
from datetime import datetime, timedelta

from core.config import Config
from core.helpers import (
    SUBSCRIPTION_PLANS, format_display_datetime, format_plan_dict,
    parse_db_datetime, parse_metadata,
)


def _ensure_wallet(cursor, conn, user_id):
    if Config.USE_POSTGRES:
        cursor.execute(
            "INSERT INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND') ON CONFLICT (user_id) DO NOTHING",
            (user_id,),
        )
    else:
        cursor.execute(
            "INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')",
            (user_id,),
        )
    conn.commit()


def get_wallet_data(conn, user_id):
    c = conn.cursor()
    _ensure_wallet(c, conn, user_id)
    c.execute('SELECT balance, currency, updated_at FROM wallets WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    wallet = {
        'balance': row[0] if row else 0,
        'currency': row[1] if row else 'VND',
        'updated_at': format_display_datetime(row[2]) if row else None,
    }
    c.execute(
        'SELECT subscription_type, amount, start_date, end_date, status, auto_renew '
        'FROM manager_subscriptions WHERE user_id = ?', (user_id,)
    )
    sub = c.fetchone()
    subscription = {
        'subscription_type': sub[0], 'amount': sub[1],
        'start_date': format_display_datetime(sub[2]),
        'end_date': format_display_datetime(sub[3]),
        'status': sub[4], 'auto_renew': sub[5],
    } if sub else None
    c.execute(
        'SELECT id, amount, type, status, created_at FROM wallet_transactions '
        'WHERE user_id = ? ORDER BY created_at DESC LIMIT 10', (user_id,)
    )
    transactions = [
        {'id': r[0], 'amount': r[1], 'type': r[2], 'status': r[3],
         'created_at': format_display_datetime(r[4])}
        for r in c.fetchall()
    ]
    plans = {key: format_plan_dict(key) for key in SUBSCRIPTION_PLANS}
    return {'wallet': wallet, 'subscription': subscription,
            'transactions': transactions, 'plans': plans}


def create_topup_request(conn, user_id, amount, method, reference, note):
    if amount < 50000:
        raise ValueError('Minimum amount is 50,000 VND')
    c = conn.cursor()
    try:
        _ensure_wallet(c, conn, user_id)
        metadata = json.dumps({'initiated_by': 'user', 'method': method, 'reference': reference})
        c.execute(
            '''INSERT INTO wallet_transactions
               (user_id, amount, currency, type, status, method, reference, notes, metadata)
               VALUES (?, ?, 'VND', ?, 'pending', ?, ?, ?, ?)''',
            (user_id, amount, 'topup', method, reference or None, note or None, metadata),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def create_withdrawal(conn, user_id, amount, bank_name, account_number, account_name, note):
    if amount < 100000:
        raise ValueError('Minimum withdrawal amount is 100,000 VND')
    c = conn.cursor()
    try:
        _ensure_wallet(c, conn, user_id)
        c.execute('SELECT balance FROM wallets WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        balance = float(row[0]) if row else 0
        if amount > balance:
            raise ValueError('Insufficient balance')
        c.execute('UPDATE wallets SET balance=balance-?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?',
                  (amount, user_id))
        metadata = json.dumps({'bank_name': bank_name, 'account_number': account_number,
                               'account_name': account_name, 'note': note})
        c.execute(
            '''INSERT INTO wallet_transactions
               (user_id, amount, currency, type, status, method, notes, metadata)
               VALUES (?, ?, 'VND', 'withdrawal', 'completed', 'bank_transfer', ?, ?)''',
            (user_id, -amount, f'Rút về {bank_name} - {account_number}', metadata),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def upgrade_subscription(conn, user_id, plan_key):
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        raise ValueError('Invalid plan')
    c = conn.cursor()
    try:
        _ensure_wallet(c, conn, user_id)
        c.execute('SELECT balance FROM wallets WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        balance = row[0] if row else 0
        if balance < plan['amount']:
            raise ValueError('Insufficient wallet balance')
        now = datetime.utcnow()
        c.execute(
            'SELECT subscription_type, amount, start_date, end_date, status, auto_renew '
            'FROM manager_subscriptions WHERE user_id = ?', (user_id,)
        )
        existing = c.fetchone()
        current_end = parse_db_datetime(existing[3]) if existing else None
        new_start = current_end if current_end and current_end > now else now
        new_end = new_start + timedelta(days=plan['days'])
        start_str = new_start.strftime('%Y-%m-%d %H:%M:%S')
        end_str = new_end.strftime('%Y-%m-%d %H:%M:%S')
        auto_renew = existing[5] if existing and existing[5] is not None else 0
        if existing:
            c.execute(
                '''UPDATE manager_subscriptions SET subscription_type=?, amount=?, start_date=?,
                   end_date=?, status='active', auto_renew=?, updated_at=CURRENT_TIMESTAMP
                   WHERE user_id=?''',
                (plan_key, plan['amount'], start_str, end_str, auto_renew, user_id),
            )
        else:
            c.execute(
                '''INSERT INTO manager_subscriptions
                   (user_id, subscription_type, amount, start_date, end_date, status, auto_renew)
                   VALUES (?, ?, ?, ?, ?, 'active', ?)''',
                (user_id, plan_key, plan['amount'], start_str, end_str, auto_renew),
            )
        c.execute(
            "UPDATE users SET role=CASE WHEN role='admin' THEN role ELSE 'manager' END, "
            'subscription_expires_at=? WHERE id=?', (end_str, user_id)
        )
        c.execute('UPDATE wallets SET balance=balance-?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?',
                  (plan['amount'], user_id))
        txn_id = f"SUB-{user_id}-{int(datetime.utcnow().timestamp())}"
        c.execute(
            '''INSERT INTO subscription_history
               (user_id, subscription_type, amount, payment_method, transaction_id, status, notes)
               VALUES (?, ?, ?, 'wallet', ?, 'completed', ?)''',
            (user_id, plan_key, plan['amount'], txn_id, f'Upgrade to {plan["name"]}'),
        )
        metadata = json.dumps({'plan': plan_key, 'transaction_id': txn_id})
        c.execute(
            '''INSERT INTO wallet_transactions
               (user_id, amount, currency, type, status, method, reference, notes, metadata)
               VALUES (?, ?, 'VND', 'subscription', 'completed', 'wallet', ?, ?, ?)''',
            (user_id, -plan['amount'], txn_id, f'Upgrade {plan["name"]}', metadata),
        )
        conn.commit()
        c.execute('SELECT balance FROM wallets WHERE user_id = ?', (user_id,))
        new_balance = c.fetchone()[0]
        return {'new_balance': new_balance, 'expires_at': format_display_datetime(end_str)}
    except Exception:
        conn.rollback()
        raise


def toggle_auto_renew(conn, user_id, enabled):
    c = conn.cursor()
    try:
        c.execute('SELECT id FROM manager_subscriptions WHERE user_id = ?', (user_id,))
        if not c.fetchone():
            raise ValueError('No subscription found')
        c.execute(
            'UPDATE manager_subscriptions SET auto_renew=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?',
            (1 if enabled else 0, user_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_pending_transactions(conn):
    """conn.row_factory phải được set thành sqlite3.Row trước khi gọi hàm này."""
    c = conn.cursor()
    c.execute(
        '''SELECT wt.id, wt.user_id, wt.amount, wt.currency, wt.type, wt.status, wt.method,
                  wt.reference, wt.notes, wt.metadata, wt.created_at,
                  u.name AS user_name, u.email AS user_email
           FROM wallet_transactions wt
           JOIN users u ON wt.user_id = u.id
           WHERE wt.status = 'pending' ORDER BY wt.created_at ASC'''
    )
    result = []
    for row in c.fetchall():
        metadata = parse_metadata(row['metadata'])
        result.append({
            'id': row['id'], 'user_id': row['user_id'], 'user_name': row['user_name'],
            'user_email': row['user_email'], 'amount': row['amount'], 'currency': row['currency'],
            'type': row['type'], 'status': row['status'], 'method': row['method'],
            'reference': row['reference'], 'notes': row['notes'], 'metadata': metadata,
            'plan_label': metadata.get('plan') or metadata.get('target_plan'),
            'created_at': format_display_datetime(row['created_at']),
        })
    return result


def process_transaction(conn, transaction_id, action, admin_id, admin_email, note):
    if action not in ('approve', 'reject'):
        raise ValueError('Invalid action')
    c = conn.cursor()
    try:
        c.execute(
            'SELECT id, user_id, amount, currency, type, status, metadata FROM wallet_transactions WHERE id = ?',
            (transaction_id,)
        )
        row = c.fetchone()
        if not row:
            raise LookupError('Transaction not found')
        if row[5] != 'pending':
            raise ValueError('Transaction already processed')
        metadata = parse_metadata(row[6])
        metadata.update({'admin_id': admin_id, 'admin_email': admin_email,
                         'admin_action_at': datetime.utcnow().isoformat()})
        if note:
            metadata['admin_note'] = note
        if action == 'approve':
            if Config.USE_POSTGRES:
                c.execute("INSERT INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND') ON CONFLICT (user_id) DO NOTHING", (row[1],))
            else:
                c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (row[1],))
            if row[2] != 0:
                c.execute('UPDATE wallets SET balance=balance+?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?',
                          (row[2], row[1]))
            c.execute(
                "UPDATE wallet_transactions SET status='completed', metadata=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (json.dumps(metadata), transaction_id),
            )
        else:
            c.execute(
                "UPDATE wallet_transactions SET status='rejected', metadata=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (json.dumps(metadata), transaction_id),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
