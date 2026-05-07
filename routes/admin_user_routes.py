"""Admin and user-management routes extracted from main_routes.py."""

import app as app_module


# Reuse initialized objects/functions from app module during migration.
for _name, _value in vars(app_module).items():
    if _name.startswith('__'):
        continue
    if _name in globals():
        continue
    globals()[_name] = _value


def register_admin_user_routes(app):
    @app.route('/api/admin/users')
    @login_required
    def admin_get_users():
        """Get all users for admin dashboard"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('''SELECT id, email, name, role, created_at FROM users ORDER BY created_at DESC''')
        users = c.fetchall()
        conn.close()

        return jsonify({
            'success': True,
            'users': [{
                'id': user[0],
                'email': user[1],
                'name': user[2],
                'role': user[3],
                'created_at': user[4]
            } for user in users]
        })

    @app.route('/api/admin/activity')
    @login_required
    def admin_get_activity():
        """Get recent activity logs"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        activities = db_manager.get_recent_activities(limit=20)
        return jsonify({'success': True, 'activities': activities})

    @app.route('/api/admin/stats')
    @login_required
    def admin_get_stats():
        """Get system statistics for admin dashboard"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        return jsonify({
            'success': True,
            'stats': {
                'users': 0,
                'managers': 0,
                'products': 0,
                'customers': 0
            }
        })

    @app.route('/api/admin/create-manager', methods=['POST'])
    @login_required
    def admin_create_manager():
        """Create a new manager (Admin only)"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        data = request.get_json()
        if not data or 'email' not in data or 'name' not in data or 'password' not in data:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        try:
            user_id = db_manager.create_user(data['email'], data['password'], data['name'], role='manager')
            return jsonify({'success': True, 'message': 'Manager created successfully', 'user_id': user_id})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400

    @app.route('/api/create-user', methods=['POST'])
    @login_required
    def create_user():
        """Create a new user account (Manager/Admin only)"""
        if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        try:
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip() or data['email'].split('@')[0]

            user_id = db_manager.create_user(
                data['email'],
                data['password'],
                full_name,
                role='employee',
                first_name=first_name,
                last_name=last_name,
                manager_id=current_user.id
            )
            return jsonify({'success': True, 'message': 'Employee account created successfully', 'user_id': user_id})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400

    @app.route('/api/users', methods=['GET'])
    @login_required
    @csrf.exempt
    def get_users():
        """Get list of users (Manager/Admin only)"""
        if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        role_filter = request.args.get('role', None)

        conn = db_manager.get_connection()
        c = conn.cursor()

        columns = db_manager.get_table_columns('users', cursor=c)
        has_first_name = 'first_name' in columns

        if has_first_name:
            if current_user.role == 'manager':
                query = '''
                    SELECT id, email, first_name, last_name, role, created_at 
                    FROM users 
                    WHERE manager_id = ?
                '''
                params = [current_user.id]

                if role_filter:
                    query += " AND role = ?"
                    params.append(role_filter)

                query += " ORDER BY created_at DESC"
                c.execute(query, tuple(params))
            else:
                if role_filter:
                    c.execute('''
                        SELECT id, email, first_name, last_name, role, created_at 
                        FROM users 
                        WHERE role = ?
                        ORDER BY created_at DESC
                    ''', (role_filter,))
                else:
                    c.execute('''
                        SELECT id, email, first_name, last_name, role, created_at 
                        FROM users 
                        ORDER BY created_at DESC
                    ''')

            users = []
            for row in c.fetchall():
                users.append({
                    'id': row[0],
                    'email': row[1],
                    'first_name': row[2] or '',
                    'last_name': row[3] or '',
                    'role': row[4],
                    'created_at': row[5]
                })
        else:
            if current_user.role == 'manager':
                query = '''
                    SELECT id, email, name, role, created_at 
                    FROM users 
                    WHERE manager_id = ?
                '''
                params = [current_user.id]

                if role_filter:
                    query += " AND role = ?"
                    params.append(role_filter)

                query += " ORDER BY created_at DESC"
                c.execute(query, tuple(params))
            else:
                if role_filter:
                    c.execute('''
                        SELECT id, email, name, role, created_at 
                        FROM users 
                        WHERE role = ?
                        ORDER BY created_at DESC
                    ''', (role_filter,))
                else:
                    c.execute('''
                        SELECT id, email, name, role, created_at 
                        FROM users 
                        ORDER BY created_at DESC
                    ''')

            users = []
            for row in c.fetchall():
                users.append({
                    'id': row[0],
                    'email': row[1],
                    'name': row[2] or '',
                    'role': row[3],
                    'created_at': row[4]
                })

        conn.close()
        return jsonify({'success': True, 'users': users})

    @app.route('/api/users/<int:user_id>', methods=['DELETE'])
    @login_required
    def delete_user_account(user_id):
        """Delete user account (Manager/Admin only)"""
        if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        if user_id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 400

        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()

        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'}), 404

        if user[0] != 'user':
            conn.close()
            return jsonify({'success': False, 'message': 'Can only delete regular users'}), 403

        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'User deleted successfully'})

    @app.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
    @login_required
    def reset_user_password(user_id):
        """Reset user password (Manager/Admin only)"""
        if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        data = request.get_json()
        if not data or 'password' not in data:
            return jsonify({'success': False, 'message': 'Missing password'}), 400

        new_password = data['password']
        if len(new_password) < 8:
            return jsonify({'success': False, 'message': 'Password must be at least 8 characters'}), 400

        conn = db_manager.get_connection()
        c = conn.cursor()

        c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()

        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'}), 404

        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash(new_password)

        c.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Password reset successfully'})

    @app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
    @login_required
    def admin_delete_user(user_id):
        """Delete user (Admin only)"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        if user_id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 400

        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'User deleted successfully'})

    @app.route('/api/admin/users/promote', methods=['POST'])
    @login_required
    def admin_promote_user():
        """Promote user to manager (Admin only)"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        data = request.get_json()
        user_id = data.get('user_id')
        new_role = data.get('role', 'manager')

        if not user_id:
            return jsonify({'success': False, 'message': 'Missing user_id'}), 400

        if user_id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot change your own role'}), 400

        if new_role not in ['manager']:
            return jsonify({'success': False, 'message': 'Can only promote to manager'}), 400

        try:
            conn = db_manager.get_connection()
            c = conn.cursor()

            c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
            user = c.fetchone()

            if not user:
                conn.close()
                return jsonify({'success': False, 'message': 'User not found'}), 404

            if user[0] == 'admin':
                conn.close()
                return jsonify({'success': False, 'message': 'Cannot change admin role'}), 400

            c.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            conn.commit()
            conn.close()

            db_manager.log_activity(current_user.id, 'Promote User', f'Promoted user {user_id} to {new_role}', request.remote_addr)

            return jsonify({'success': True, 'message': f'User promoted to {new_role} successfully'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/admin/users/demote', methods=['POST'])
    @login_required
    def admin_demote_user():
        """Demote manager to user (Admin only)"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        data = request.get_json()
        user_id = data.get('user_id')
        new_role = data.get('role', 'user')

        if not user_id:
            return jsonify({'success': False, 'message': 'Missing user_id'}), 400

        if user_id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot change your own role'}), 400

        if new_role not in ['user']:
            return jsonify({'success': False, 'message': 'Can only demote to user'}), 400

        try:
            conn = db_manager.get_connection()
            c = conn.cursor()

            c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
            user = c.fetchone()

            if not user:
                conn.close()
                return jsonify({'success': False, 'message': 'User not found'}), 404

            if user[0] == 'admin':
                conn.close()
                return jsonify({'success': False, 'message': 'Cannot change admin role'}), 400

            c.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            conn.commit()
            conn.close()

            db_manager.log_activity(current_user.id, 'Demote User', f'Demoted user {user_id} to {new_role}', request.remote_addr)

            return jsonify({'success': True, 'message': f'User demoted to {new_role} successfully'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/manager/users-permissions')
    @login_required
    def manager_get_users_permissions():
        """Get all users with their permissions (Manager/Admin only)"""
        if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

        try:
            users = db_manager.get_all_users_with_permissions()
            return jsonify({'success': True, 'users': users})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500