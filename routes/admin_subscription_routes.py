"""Admin subscription-management routes extracted from main_routes.py."""

import app as app_module


# Reuse initialized objects/functions from app module during migration.
for _name, _value in vars(app_module).items():
    if _name.startswith('__'):
        continue
    if _name in globals():
        continue
    globals()[_name] = _value


def register_admin_subscription_routes(app):
    @app.route('/api/admin/subscriptions', methods=['GET'])
    @login_required
    def api_get_subscriptions():
        """Get all manager subscriptions"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        conn = db_manager.get_connection()
        c = conn.cursor()

        c.execute('''SELECT 
                        s.id, s.user_id, s.subscription_type, s.amount, 
                        s.start_date, s.end_date, s.status, s.auto_renew,
                        u.name as user_name, u.email as user_email
                    FROM manager_subscriptions s
                    JOIN users u ON s.user_id = u.id
                    ORDER BY s.end_date DESC''')

        subscriptions = []
        for row in c.fetchall():
            subscriptions.append({
                'id': row[0],
                'user_id': row[1],
                'subscription_type': row[2],
                'amount': row[3],
                'start_date': row[4],
                'end_date': row[5],
                'status': row[6],
                'auto_renew': bool(row[7]) if len(row) > 7 and row[7] is not None else False,
                'user_name': row[8] if len(row) > 8 else 'Unknown',
                'user_email': row[9] if len(row) > 9 else 'Unknown'
            })

        conn.close()
        return jsonify({'success': True, 'subscriptions': subscriptions})

    @app.route('/api/admin/subscription/auto-renew', methods=['POST'])
    @login_required
    @csrf.exempt
    def api_toggle_auto_renew():
        """Toggle auto-renew for a subscription"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        data = request.get_json()
        user_id = data.get('user_id')
        auto_renew = data.get('auto_renew', False)

        if not user_id:
            return jsonify({'success': False, 'message': 'Missing user_id'}), 400

        try:
            conn = db_manager.get_connection()
            c = conn.cursor()

            columns = db_manager.get_table_columns('manager_subscriptions', cursor=c)

            if 'auto_renew' not in columns:
                c.execute("ALTER TABLE manager_subscriptions ADD COLUMN auto_renew INTEGER DEFAULT 0")
                conn.commit()

            c.execute('''UPDATE manager_subscriptions 
                         SET auto_renew = ? 
                         WHERE user_id = ? AND status = 'active' ''',
                      (1 if auto_renew else 0, user_id))
            conn.commit()
            conn.close()

            return jsonify({'success': True, 'message': 'Auto-renew updated'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/subscription/extend', methods=['POST'])
    @login_required
    @csrf.exempt
    def api_extend_subscription():
        """Extend a manager's subscription"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        data = request.get_json()
        user_id = data.get('user_id')
        plan_type = data.get('plan_type')
        payment_method = data.get('payment_method', 'manual')
        transaction_id = data.get('transaction_id', f'MANUAL-{secrets.token_hex(4).upper()}')

        if not user_id or not plan_type:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        plans = {
            'monthly': {'days': 30, 'amount': 500000},
            'quarterly': {'days': 90, 'amount': 1200000},
            'yearly': {'days': 365, 'amount': 4000000},
            'trial': {'days': 30, 'amount': 0}
        }

        if plan_type not in plans:
            return jsonify({'success': False, 'message': 'Invalid plan type'}), 400

        plan_info = plans[plan_type]
        duration_days = plan_info['days']
        amount = plan_info['amount']

        try:
            conn = db_manager.get_connection()
            c = conn.cursor()

            c.execute("SELECT end_date FROM manager_subscriptions WHERE user_id = ?", (user_id,))
            row = c.fetchone()

            current_date = datetime.now()
            start_date = current_date

            if row and row[0]:
                current_end_str = row[0]
                try:
                    current_end = datetime.strptime(current_end_str, '%Y-%m-%d')
                    if current_end > current_date:
                        start_date = current_end
                except ValueError:
                    pass

            new_end_date = start_date + timedelta(days=duration_days)
            new_end_date_str = new_end_date.strftime('%Y-%m-%d')

            if Config.USE_POSTGRES:
                c.execute('''INSERT INTO manager_subscriptions 
                         (user_id, subscription_type, amount, start_date, end_date, status, auto_renew)
                         VALUES (?, ?, ?, ?, ?, 'active', 0)
                         ON CONFLICT (user_id) DO UPDATE SET 
                         subscription_type=excluded.subscription_type,
                         amount=excluded.amount,
                         start_date=excluded.start_date,
                         end_date=excluded.end_date,
                         status='active'
                         ''',
                      (user_id, plan_type, amount, datetime.now().strftime('%Y-%m-%d'), new_end_date_str))
            else:
                c.execute('''INSERT OR REPLACE INTO manager_subscriptions 
                         (user_id, subscription_type, amount, start_date, end_date, status, auto_renew)
                         VALUES (?, ?, ?, ?, ?, 'active', 0)''',
                      (user_id, plan_type, amount, datetime.now().strftime('%Y-%m-%d'), new_end_date_str))

            c.execute('''INSERT INTO subscription_history 
                         (user_id, subscription_type, amount, payment_date, payment_method, transaction_id, status)
                         VALUES (?, ?, ?, ?, ?, ?, 'Completed')''',
                      (user_id, plan_type, amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), payment_method, transaction_id))

            conn.commit()
            conn.close()

            return jsonify({
                'success': True,
                'message': f'Subscription extended until {new_end_date_str}',
                'new_expiry': new_end_date_str
            })

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/subscription-history', methods=['GET'])
    @login_required
    def api_get_subscription_history():
        """Get subscription payment history"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        conn = db_manager.get_connection()
        c = conn.cursor()

        c.execute('''
            SELECT * FROM (
                SELECT 
                    h.id, h.user_id, h.subscription_type as type, h.amount,
                    h.payment_date as date, h.payment_method as method, 
                    h.transaction_id as ref, h.status,
                    u.name as user_name
                FROM subscription_history h
                JOIN users u ON h.user_id = u.id

                UNION ALL

                SELECT 
                    t.id, t.user_id, t.type, t.amount,
                    t.created_at as date, t.method, 
                    t.reference as ref, t.status,
                    u.name as user_name
                FROM wallet_transactions t
                JOIN users u ON t.user_id = u.id
                WHERE t.status = 'completed'
            )
            ORDER BY date DESC
            LIMIT 50
        ''')

        history = []
        for row in c.fetchall():
            history.append({
                'id': row[0],
                'user_id': row[1],
                'subscription_type': row[2],
                'amount': row[3],
                'payment_date': row[4],
                'payment_method': row[5],
                'transaction_id': row[6],
                'status': row[7],
                'user_name': row[8]
            })

        conn.close()
        return jsonify({'success': True, 'history': history})

    @app.route('/api/admin/extend-subscription', methods=['POST'])
    @login_required
    def api_extend_subscription_v2():
        """Extend manager subscription"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        from datetime import datetime, timedelta

        data = request.get_json()
        user_id = data.get('user_id')
        subscription_type = data.get('subscription_type')
        payment_method = data.get('payment_method')
        transaction_id = data.get('transaction_id', '')

        plans = {
            'monthly': {'days': 30, 'amount': 500000},
            'quarterly': {'days': 90, 'amount': 1200000},
            'yearly': {'days': 365, 'amount': 4000000}
        }

        if subscription_type not in plans:
            return jsonify({'success': False, 'message': 'Invalid subscription type'}), 400

        plan = plans[subscription_type]

        conn = db_manager.get_connection()
        c = conn.cursor()

        try:
            c.execute('SELECT end_date FROM manager_subscriptions WHERE user_id = ?', (user_id,))
            current_sub = c.fetchone()

            now = datetime.now()
            if current_sub:
                current_end = datetime.strptime(current_sub[0], '%Y-%m-%d %H:%M:%S')
                start_date = max(now, current_end)
            else:
                start_date = now

            end_date = start_date + timedelta(days=plan['days'])

            if current_sub:
                c.execute('''UPDATE manager_subscriptions 
                            SET subscription_type = ?, amount = ?, 
                                start_date = ?, end_date = ?, 
                                status = 'active', payment_method = ?,
                                transaction_id = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ?''',
                         (subscription_type, plan['amount'],
                          start_date.strftime('%Y-%m-%d %H:%M:%S'),
                          end_date.strftime('%Y-%m-%d %H:%M:%S'),
                          payment_method, transaction_id, user_id))
            else:
                c.execute('''INSERT INTO manager_subscriptions 
                            (user_id, subscription_type, amount, start_date, end_date, 
                             status, payment_method, transaction_id)
                            VALUES (?, ?, ?, ?, ?, 'active', ?, ?)''',
                         (user_id, subscription_type, plan['amount'],
                          start_date.strftime('%Y-%m-%d %H:%M:%S'),
                          end_date.strftime('%Y-%m-%d %H:%M:%S'),
                          payment_method, transaction_id))

            c.execute('UPDATE users SET subscription_expires_at = ? WHERE id = ?',
                     (end_date.strftime('%Y-%m-%d %H:%M:%S'), user_id))

            c.execute('''INSERT INTO subscription_history 
                        (user_id, subscription_type, amount, payment_method, 
                         transaction_id, status)
                        VALUES (?, ?, ?, ?, ?, 'completed')''',
                     (user_id, subscription_type, plan['amount'],
                      payment_method, transaction_id))

            conn.commit()
            return jsonify({'success': True, 'message': 'Subscription extended successfully'})

        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()

    @app.route('/api/admin/check-expired-subscriptions', methods=['POST'])
    @login_required
    def api_check_expired_subscriptions():
        """Check and demote expired manager subscriptions"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        from datetime import datetime

        conn = db_manager.get_connection()
        c = conn.cursor()

        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            c.execute('''SELECT user_id FROM manager_subscriptions 
                        WHERE end_date < ? AND status = 'active' ''', (now,))
            expired_users = c.fetchall()

            demoted_count = 0
            for (user_id,) in expired_users:
                c.execute('''UPDATE manager_subscriptions 
                            SET status = 'expired', updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ?''', (user_id,))
                c.execute('UPDATE users SET role = ? WHERE id = ?', ('user', user_id))
                demoted_count += 1

            conn.commit()
            return jsonify({
                'success': True,
                'demoted_count': demoted_count,
                'message': f'Demoted {demoted_count} expired managers'
            })

        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()