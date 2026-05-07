"""Analytics, dashboard, reports, and automation routes extracted from main_routes.py."""

import app as app_module


# Reuse initialized objects/functions from app module during migration.
for _name, _value in vars(app_module).items():
    if _name.startswith('__'):
        continue
    if _name in globals():
        continue
    globals()[_name] = _value


def register_operations_routes(app):
    @app.route('/api/admin/analytics/data', methods=['GET'])
    @login_required
    def api_get_analytics_data():
        """Get Google Analytics Data"""
        if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        property_id = request.args.get('property_id')

        if request.args.get('force') in ('1', 'true', 'yes'):
            try:
                cache_file = os.path.join(os.getcwd(), 'secrets', 'ga_cache.json')
                if os.path.exists(cache_file):
                    os.remove(cache_file)
                    print('Cache cleared via force param')
            except Exception as e:
                print('Failed to clear cache via force param:', e)

        result = analytics_service.get_report(property_id)
        return jsonify(result)

    @app.route('/api/admin/analytics/clear_cache', methods=['POST'])
    @login_required
    def api_admin_clear_analytics_cache():
        if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        try:
            cache_file = os.path.join(os.getcwd(), 'secrets', 'ga_cache.json')
            if os.path.exists(cache_file):
                os.remove(cache_file)
                return jsonify({'success': True, 'message': 'Cache cleared'})
            return jsonify({'success': False, 'message': 'No cache file'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/dashboard/stats', methods=['GET'])
    @login_required
    def api_get_dashboard_stats():
        """Get dashboard statistics"""
        try:
            conn = db_manager.get_connection()
            c = conn.cursor()

            today = datetime.now()
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
            c.execute("SELECT SUM(total_amount) FROM export_transactions WHERE created_at >= ?", (start_of_month,))
            revenue = c.fetchone()[0] or 0

            start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
            c.execute("SELECT COUNT(*) FROM export_transactions WHERE created_at >= ?", (start_of_day,))
            new_orders = c.fetchone()[0] or 0

            pending_returns = 0
            credits = 100

            c.execute("SELECT COUNT(*) FROM workflows WHERE user_id = ?", (current_user.id,))
            active_projects = c.fetchone()[0] or 0

            conn.close()

            return jsonify({
                'success': True,
                'revenue': revenue,
                'new_orders': new_orders,
                'pending_returns': pending_returns,
                'credits': credits,
                'active_projects': active_projects,
                'subscription_status': 'Active'
            })
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/reports/stats', methods=['GET'])
    @login_required
    def api_get_report_stats():
        """Get revenue, expense, profit stats for current month"""
        conn = db_manager.get_connection()
        c = conn.cursor()

        today = datetime.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')

        c.execute("SELECT SUM(total_amount) FROM export_transactions WHERE created_at >= ?", (start_of_month,))
        revenue = c.fetchone()[0] or 0

        c.execute("SELECT SUM(total_amount) FROM import_transactions WHERE created_at >= ?", (start_of_month,))
        expense = c.fetchone()[0] or 0

        profit = revenue - expense

        c.execute("SELECT COUNT(*) FROM scheduled_reports WHERE last_sent_at >= ?", (start_of_month,))
        reports_sent = c.fetchone()[0] or 0

        conn.close()
        return jsonify({
            'success': True,
            'revenue': revenue,
            'expense': expense,
            'profit': profit,
            'reports_sent': reports_sent
        })

    @app.route('/api/reports/scheduled', methods=['GET'])
    @login_required
    def api_get_scheduled_reports():
        """Get all scheduled reports"""
        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM scheduled_reports ORDER BY created_at DESC')
        reports = []
        for row in c.fetchall():
            reports.append({
                'id': row[0], 'name': row[1], 'report_type': row[2],
                'frequency': row[3], 'channel': row[4], 'recipients': row[5],
                'status': row[6], 'last_sent_at': row[7]
            })
        conn.close()
        return jsonify({'success': True, 'reports': reports})

    @app.route('/api/reports/scheduled', methods=['POST'])
    @login_required
    def api_create_scheduled_report():
        """Create a scheduled report"""
        data = request.get_json()
        name = data.get('name')
        report_type = data.get('report_type')
        frequency = data.get('frequency')
        channel = data.get('channel')
        recipients = data.get('recipients')

        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO scheduled_reports 
                         (name, report_type, frequency, channel, recipients, created_by)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (name, report_type, frequency, channel, recipients, current_user.id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Report scheduled successfully'})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()

    @app.route('/api/reports/scheduled/<int:report_id>', methods=['DELETE'])
    @login_required
    def api_delete_scheduled_report(report_id):
        """Delete a scheduled report"""
        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM scheduled_reports WHERE id = ?', (report_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Report deleted successfully'})

    @app.route('/api/automations', methods=['GET'])
    @login_required
    def api_get_automations():
        """Get all automations"""
        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM se_automations ORDER BY created_at DESC')
        automations = []
        for row in c.fetchall():
            automations.append({
                'id': row[0], 'name': row[1], 'type': row[2],
                'config': json.loads(row[3]) if row[3] else {},
                'status': 'active' if row[4] else 'inactive',
                'enabled': bool(row[4]), 'last_run': row[5]
            })
        conn.close()
        return jsonify({'success': True, 'automations': automations})

    @app.route('/api/automations', methods=['POST'])
    @login_required
    def api_create_automation():
        """Create an automation"""
        data = request.get_json()
        name = data.get('name')
        type = data.get('type')

        config_input = data.get('config', {})
        if isinstance(config_input, str):
            try:
                json.loads(config_input)
                config = config_input
            except Exception:
                config = json.dumps(config_input)
        else:
            config = json.dumps(config_input)

        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO se_automations 
                         (name, type, config, created_by)
                         VALUES (?, ?, ?, ?)''',
                      (name, type, config, current_user.id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Automation created successfully'})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()

    @app.route('/api/automations/<int:automation_id>', methods=['PUT'])
    @login_required
    def api_update_automation(automation_id):
        """Update an automation (status or config)"""
        data = request.get_json()

        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            c.execute('SELECT id FROM se_automations WHERE id = ?', (automation_id,))
            if not c.fetchone():
                return jsonify({'success': False, 'message': 'Automation not found'}), 404

            if 'status' in data:
                enabled = 1 if data['status'] == 'active' else 0
                c.execute('UPDATE se_automations SET enabled = ? WHERE id = ?', (enabled, automation_id))

            if 'name' in data:
                c.execute('UPDATE se_automations SET name = ? WHERE id = ?', (data['name'], automation_id))

            if 'config' in data:
                config_input = data['config']
                if isinstance(config_input, str):
                    try:
                        json.loads(config_input)
                        config = config_input
                    except Exception:
                        config = json.dumps(config_input)
                else:
                    config = json.dumps(config_input)
                c.execute('UPDATE se_automations SET config = ? WHERE id = ?', (config, automation_id))

            conn.commit()
            return jsonify({'success': True, 'message': 'Automation updated successfully'})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()

    @app.route('/api/automations/<int:automation_id>', methods=['DELETE'])
    @login_required
    def api_delete_automation(automation_id):
        """Delete an automation"""
        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM se_automations WHERE id = ?', (automation_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Automation deleted successfully'})