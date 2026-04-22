"""Wallet, subscription, and profile routes extracted from main_routes."""

import app as app_module

# Reuse initialized objects/functions from app module during migration.
for _name, _value in vars(app_module).items():
    if _name.startswith('__'):
        continue
    if _name in globals():
        continue
    globals()[_name] = _value

def register_wallet_routes(app):
    @app.route('/wallet')
    @login_required
    def wallet_dashboard():
        return render_template('wallet.html', user=current_user)
    
    
    @app.route('/api/user/wallet')
    @login_required
    def api_get_wallet():
        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            # Get wallet (Read-first optimization)
            c.execute('SELECT balance, currency, updated_at FROM wallets WHERE user_id = ?', (current_user.id,))
            wallet_row = c.fetchone()
    
            if not wallet_row:
                # Ensure user has a wallet row
                if Config.USE_POSTGRES:
                     c.execute("INSERT INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND') ON CONFLICT (user_id) DO NOTHING", (current_user.id,))
                else:
                     c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (current_user.id,))
                conn.commit()
                # Fetch again
                c.execute('SELECT balance, currency, updated_at FROM wallets WHERE user_id = ?', (current_user.id,))
                wallet_row = c.fetchone()
    
            wallet_data = {
                'balance': wallet_row[0] if wallet_row else 0,
                'currency': wallet_row[1] if wallet_row else 'VND',
                'updated_at': format_display_datetime(wallet_row[2]) if wallet_row else None
            }
    
            # Get subscription
            c.execute('''SELECT subscription_type, amount, start_date, end_date, status, auto_renew
                         FROM manager_subscriptions WHERE user_id = ?''', (current_user.id,))
            sub_row = c.fetchone()
            subscription_data = None
            if sub_row:
                subscription_data = {
                    'subscription_type': sub_row[0],
                    'amount': sub_row[1],
                    'start_date': format_display_datetime(sub_row[2]),
                    'end_date': format_display_datetime(sub_row[3]),
                    'status': sub_row[4],
                    'auto_renew': sub_row[5]
                }
    
            # Recent transactions
            c.execute('''SELECT id, amount, type, status, created_at
                         FROM wallet_transactions
                         WHERE user_id = ?
                         ORDER BY created_at DESC
                         LIMIT 10''', (current_user.id,))
            transactions = [{
                'id': row[0], 'amount': row[1], 'type': row[2], 'status': row[3], 'created_at': format_display_datetime(row[4])
            } for row in c.fetchall()]
    
            plans = {key: format_plan_dict(key) for key in SUBSCRIPTION_PLANS.keys()}
    
            return jsonify({'success': True, 'wallet': wallet_data, 'subscription': subscription_data, 'transactions': transactions, 'plans': plans})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
    
    
    @app.route('/api/session')
    def api_session():
        """Return session status for the current client (used by JS to detect session expiration)."""
        if not current_user.is_authenticated:
            return jsonify({'authenticated': False})
        return jsonify({'authenticated': True, 'user': {
            'id': current_user.id,
            'email': current_user.email,
            'name': current_user.name,
            'role': getattr(current_user, 'role', 'user')
        }})
    
    
    @app.route('/api/user/profile', methods=['POST'])
    @login_required
    def api_update_profile():
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'success': False, 'message': 'Name is required'}), 400
            
        conn = db_manager.get_connection()
        try:
            c = conn.cursor()
            c.execute("UPDATE users SET name = ? WHERE id = ?", (name, current_user.id))
            conn.commit()
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
    
    
    @app.route('/api/settings/update', methods=['POST'])
    @login_required
    def api_update_settings():
        data = request.get_json()
        setting_key = data.get('key')
        setting_value = data.get('value')
        group_name = data.get('group')
        
        if not setting_key:
            return jsonify({'success': False, 'message': 'Missing setting key'}), 400
            
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                # Upsert logic
                cursor.execute("""
                    INSERT INTO system_settings (key, value, group_name, updated_at) 
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET 
                        value=excluded.value, 
                        updated_at=CURRENT_TIMESTAMP
                """, (setting_key, setting_value, group_name))
                conn.commit()
                
            return jsonify({'success': True, 'message': 'Setting updated'})
        except Exception as e:
            print(f"Error updating setting: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
    
    
    @app.route('/api/user/wallet/topup', methods=['POST'])
    @login_required
    def api_topup_wallet():
        data = request.get_json() or {}
        try:
            amount = int(data.get('amount', 0))
        except (TypeError, ValueError):
            amount = 0
    
        if amount < 50000:
            return jsonify({'success': False, 'message': 'Minimum amount is 50,000 VND'}), 400
    
        method = (data.get('method') or 'bank_transfer').strip()
        reference = (data.get('reference') or '').strip()[:120]
        note = (data.get('note') or '').strip()[:200]
    
        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            if Config.USE_POSTGRES:
                 c.execute("INSERT INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND') ON CONFLICT (user_id) DO NOTHING", (current_user.id,))
            else:
                 c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (current_user.id,))        
    
            metadata = json.dumps({'initiated_by': 'user', 'method': method, 'reference': reference})
    
            c.execute('''INSERT INTO wallet_transactions
                         (user_id, amount, currency, type, status, method, reference, notes, metadata)
                         VALUES (?, ?, 'VND', ?, 'pending', ?, ?, ?, ?)''',
                      (current_user.id, amount, 'topup', method, reference or None, note or None, metadata))
            conn.commit()
    
            return jsonify({'success': True, 'message': 'Top-up request submitted. Admin will confirm shortly.'})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
    
    
    @app.route('/api/admin/wallet/withdraw', methods=['POST'])
    @login_required
    @csrf.exempt
    def api_admin_withdraw():
        """Admin withdraw money from wallet to bank account"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
        data = request.get_json() or {}
        try:
            amount = int(data.get('amount', 0))
        except (TypeError, ValueError):
            amount = 0
        
        if amount < 100000:
            return jsonify({'success': False, 'message': 'Minimum withdrawal amount is 100,000 VND'}), 400
        
        bank_name = (data.get('bank_name') or '').strip()
        account_number = (data.get('account_number') or '').strip()
        account_name = (data.get('account_name') or '').strip()
        note = (data.get('note') or '').strip()
        
        if not bank_name or not account_number or not account_name:
            return jsonify({'success': False, 'message': 'Please provide complete bank information'}), 400
        
        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            if Config.USE_POSTGRES:
                 c.execute("INSERT INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND') ON CONFLICT (user_id) DO NOTHING", (current_user.id,))
            else:
                 c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (current_user.id,))
                 
            c.execute('SELECT balance FROM wallets WHERE user_id = ?', (current_user.id,))
            row = c.fetchone()
            balance = float(row[0]) if row else 0
            
            if amount > balance:
                return jsonify({'success': False, 'message': 'Insufficient balance'}), 400
            
            # Deduct balance
            c.execute('UPDATE wallets SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?',
                      (amount, current_user.id))
            
            # Create withdrawal transaction
            metadata = json.dumps({
                'bank_name': bank_name,
                'account_number': account_number,
                'account_name': account_name,
                'note': note
            })
            
            c.execute('''INSERT INTO wallet_transactions
                         (user_id, amount, currency, type, status, method, notes, metadata)
                         VALUES (?, ?, 'VND', 'withdrawal', 'completed', 'bank_transfer', ?, ?)''',
                      (current_user.id, -amount, f'Rút về {bank_name} - {account_number}', metadata))
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Withdrawal request submitted. Funds will be transferred within 1-2 business days.'})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
    
    
    @app.route('/api/user/subscription/upgrade', methods=['POST'])
    @login_required
    def api_upgrade_subscription():
        data = request.get_json() or {}
        plan_key = data.get('plan')
        if plan_key is None:
            return jsonify({'success': False, 'message': 'Invalid plan'}), 400
        plan_key = str(plan_key)
        plan = SUBSCRIPTION_PLANS.get(plan_key)
        if not plan:
            return jsonify({'success': False, 'message': 'Invalid plan'}), 400
    
        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            if Config.USE_POSTGRES:
                 c.execute("INSERT INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND') ON CONFLICT (user_id) DO NOTHING", (current_user.id,))
            else:
                 c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (current_user.id,))
                 
            c.execute('SELECT balance FROM wallets WHERE user_id = ?', (current_user.id,))
            wallet_row = c.fetchone()
            balance = wallet_row[0] if wallet_row else 0
    
            if balance < plan['amount']:
                conn.rollback()
                return jsonify({'success': False, 'message': 'Insufficient wallet balance to upgrade this plan'}), 400
    
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            c.execute('SELECT subscription_type, amount, start_date, end_date, status, auto_renew FROM manager_subscriptions WHERE user_id = ?', (current_user.id,))
            existing = c.fetchone()
            current_end = parse_db_datetime(existing[3]) if existing else None
            new_start = current_end if current_end and current_end > now else now
            new_end = new_start + timedelta(days=plan['days'])
            start_str = new_start.strftime('%Y-%m-%d %H:%M:%S')
            end_str = new_end.strftime('%Y-%m-%d %H:%M:%S')
    
            auto_renew = existing[5] if existing and existing[5] is not None else 0
            if existing:
                c.execute('''UPDATE manager_subscriptions
                             SET subscription_type = ?, amount = ?, start_date = ?, end_date = ?, status = 'active', auto_renew = ?, updated_at = CURRENT_TIMESTAMP
                             WHERE user_id = ?''', (plan_key, plan['amount'], start_str, end_str, auto_renew, current_user.id))
            else:
                c.execute('''INSERT INTO manager_subscriptions (user_id, subscription_type, amount, start_date, end_date, status, auto_renew)
                             VALUES (?, ?, ?, ?, ?, 'active', ?)''', (current_user.id, plan_key, plan['amount'], start_str, end_str, auto_renew))
    
            c.execute('''UPDATE users SET role = CASE WHEN role = 'admin' THEN role ELSE 'manager' END, subscription_expires_at = ? WHERE id = ?''', (end_str, current_user.id))
    
            c.execute('''UPDATE wallets SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?''', (plan['amount'], current_user.id))
    
            txn_id = f"SUB-{current_user.id}-{int(datetime.utcnow().timestamp())}"
            c.execute('''INSERT INTO subscription_history (user_id, subscription_type, amount, payment_method, transaction_id, status, notes)
                         VALUES (?, ?, ?, 'wallet', ?, 'completed', ?)''', (current_user.id, plan_key, plan['amount'], txn_id, f'Upgrade to {plan["name"]}'))
    
            metadata = json.dumps({'plan': plan_key, 'transaction_id': txn_id})
            c.execute('''INSERT INTO wallet_transactions (user_id, amount, currency, type, status, method, reference, notes, metadata)
                         VALUES (?, ?, 'VND', 'subscription', 'completed', 'wallet', ?, ?, ?)''', (current_user.id, -plan['amount'], txn_id, f'Upgrade {plan["name"]}', metadata))
    
            conn.commit()
    
            c.execute('SELECT balance FROM wallets WHERE user_id = ?', (current_user.id,))
            new_balance = c.fetchone()[0]
    
            return jsonify({'success': True, 'message': 'Upgrade successful.', 'balance': new_balance, 'expires_at': format_display_datetime(end_str)})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
    
    
    @app.route('/api/user/subscription/auto-renew', methods=['POST'])
    @login_required
    def api_user_toggle_auto_renew():
        data = request.get_json() or {}
        enabled = data.get('enabled')
        if enabled is None:
            return jsonify({'success': False, 'message': 'Invalid parameter: enabled'}), 400
    
        enabled_flag = 1 if bool(enabled) else 0
    
        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            c.execute('SELECT id FROM manager_subscriptions WHERE user_id = ?', (current_user.id,))
            if not c.fetchone():
                return jsonify({'success': False, 'message': 'No subscription found to toggle auto-renew'}), 400
    
            c.execute('''UPDATE manager_subscriptions SET auto_renew = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?''', (enabled_flag, current_user.id))
            conn.commit()
    
            return jsonify({'success': True, 'message': 'Auto-renew updated'})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
    
    
    @app.route('/api/admin/wallet/pending', methods=['GET'])
    @login_required
    def api_admin_pending_wallet_transactions():
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
        conn = db_manager.get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute('''SELECT wt.id, wt.user_id, wt.amount, wt.currency, wt.type, wt.status, wt.method, wt.reference, wt.notes, wt.metadata, wt.created_at, u.name AS user_name, u.email AS user_email
                         FROM wallet_transactions wt
                         JOIN users u ON wt.user_id = u.id
                         WHERE wt.status = 'pending' ORDER BY wt.created_at ASC''')
            rows = c.fetchall()
            transactions = []
            for row in rows:
                metadata = parse_metadata(row['metadata'])
                plan_hint = metadata.get('plan') or metadata.get('target_plan')
                transactions.append({
                    'id': row['id'], 'user_id': row['user_id'], 'user_name': row['user_name'], 'user_email': row['user_email'], 'amount': row['amount'], 'currency': row['currency'], 'type': row['type'], 'status': row['status'], 'method': row['method'], 'reference': row['reference'], 'notes': row['notes'], 'metadata': metadata, 'plan_label': plan_hint, 'created_at': format_display_datetime(row['created_at'])
                })
            return jsonify({'success': True, 'transactions': transactions})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
    
    
    @app.route('/api/admin/wallet/pending/<int:transaction_id>', methods=['POST'])
    @login_required
    def api_admin_process_wallet_transaction(transaction_id):
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
        data = request.get_json() or {}
        action = data.get('action')
        note = (data.get('note') or '').strip()
        if action not in ['approve', 'reject']:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400
    
        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            c.execute('SELECT id, user_id, amount, currency, type, status, metadata FROM wallet_transactions WHERE id = ?', (transaction_id,))
            row = c.fetchone()
            if not row:
                return jsonify({'success': False, 'message': 'Transaction not found'}), 404
            if row[5] != 'pending':
                return jsonify({'success': False, 'message': 'Transaction has already been processed'}), 400
    
            metadata = parse_metadata(row[6])
            metadata.update({'admin_id': current_user.id, 'admin_email': current_user.email, 'admin_action_at': datetime.utcnow().isoformat()})
            if note:
                metadata['admin_note'] = note
    
            if action == 'approve':
                if Config.USE_POSTGRES:
                     c.execute("INSERT INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND') ON CONFLICT (user_id) DO NOTHING", (row[1],))
                else:
                     c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (row[1],))
                if row[2] != 0:
                    c.execute('UPDATE wallets SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', (row[2], row[1]))
                c.execute("UPDATE wallet_transactions SET status = 'completed', metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(metadata), transaction_id))
                conn.commit()
                return jsonify({'success': True, 'message': 'Transaction approved and wallet updated.'})
            else:
                c.execute("UPDATE wallet_transactions SET status = 'rejected', metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(metadata), transaction_id))
                conn.commit()
                return jsonify({'success': True, 'message': 'Transaction rejected.'})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()
