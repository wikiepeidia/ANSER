"""Workspace builder and scenario API routes extracted from main_routes."""

import app as app_module


# Reuse initialized objects/functions from app module during migration.
for _name, _value in vars(app_module).items():
    if _name.startswith('__'):
        continue
    if _name in globals():
        continue
    globals()[_name] = _value


def register_workspace_routes(app):
    @app.route('/api/workspaces')
    @login_required
    def get_workspaces():
        """Get all workspaces for current user"""
        try:
            workspaces = auth_manager.get_user_workspaces(current_user.id)
            return jsonify([
                {
                    'id': w[0],
                    'name': w[2],
                    'type': w[3],
                    'description': w[4],
                    'created_at': w[6],
                }
                for w in workspaces
            ])
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/workspace/<int:workspace_id>/items')
    @login_required
    def get_workspace_items(workspace_id):
        """Get all items in a workspace"""
        conn = db_manager.get_connection()
        c = conn.cursor()

        try:
            c.execute('SELECT id FROM workspaces WHERE id = ? AND user_id = ?', (workspace_id, current_user.id))
            if not c.fetchone():
                return jsonify({'success': False, 'message': 'Workspace not found or access denied'}), 403

            c.execute('''SELECT * FROM items WHERE workspace_id = ? ORDER BY created_at DESC''', (workspace_id,))
            items = c.fetchall()

            return jsonify([
                {
                    'id': item[0],
                    'title': item[2],
                    'description': item[3],
                    'type': item[4],
                    'status': item[5],
                    'priority': item[6],
                    'created_at': item[9],
                }
                for item in items
            ])
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
        finally:
            conn.close()

    @app.route('/api/workspace/<int:workspace_id>/items', methods=['POST'])
    @login_required
    def create_item(workspace_id):
        """Create new item in workspace"""
        data = request.get_json()

        if not data or 'title' not in data:
            return jsonify({'success': False, 'message': 'Missing required field: title'}), 400

        if not data['title'].strip():
            return jsonify({'success': False, 'message': 'Item title cannot be empty'}), 400

        conn = db_manager.get_connection()
        c = conn.cursor()

        try:
            c.execute('SELECT id FROM workspaces WHERE id = ? AND user_id = ?', (workspace_id, current_user.id))
            if not c.fetchone():
                return jsonify({'success': False, 'message': 'Workspace not found or access denied'}), 403

            c.execute(
                '''INSERT INTO items (workspace_id, title, description, type, status, priority, assignee_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (
                    workspace_id,
                    data['title'].strip(),
                    data.get('description', ''),
                    data.get('type', 'task'),
                    data.get('status', 'todo'),
                    data.get('priority', 'medium'),
                    current_user.id,
                ),
            )

            item_id = c.lastrowid
            conn.commit()

            return jsonify({'success': True, 'item_id': item_id, 'message': 'Item created successfully'})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
        finally:
            conn.close()

    @app.route('/api/items/<int:item_id>', methods=['PUT'])
    @login_required
    def update_item(item_id):
        """Update existing item"""
        data = request.get_json()

        if not data or 'title' not in data:
            return jsonify({'success': False, 'message': 'Missing required field: title'}), 400

        if not data['title'].strip():
            return jsonify({'success': False, 'message': 'Item title cannot be empty'}), 400

        conn = db_manager.get_connection()
        c = conn.cursor()

        try:
            c.execute(
                '''UPDATE items SET title = ?, description = ?, status = ?, priority = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND assignee_id = ?''',
                (
                    data['title'].strip(),
                    data.get('description', ''),
                    data.get('status', 'todo'),
                    data.get('priority', 'medium'),
                    item_id,
                    current_user.id,
                ),
            )

            conn.commit()

            if c.rowcount > 0:
                return jsonify({'success': True, 'message': 'Item updated successfully'})
            return jsonify({'success': False, 'message': 'Item not found or unauthorized'}), 404
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
        finally:
            conn.close()

    @app.route('/api/items/<int:item_id>', methods=['DELETE'])
    @login_required
    def delete_item(item_id):
        """Delete item"""
        conn = db_manager.get_connection()
        c = conn.cursor()

        try:
            c.execute('DELETE FROM items WHERE id = ? AND assignee_id = ?', (item_id, current_user.id))
            conn.commit()

            if c.rowcount > 0:
                return jsonify({'success': True, 'message': 'Item deleted successfully'})
            return jsonify({'success': False, 'message': 'Item not found or unauthorized'}), 404
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
        finally:
            conn.close()

    @app.route('/api/workspace', methods=['POST'])
    @login_required
    def create_workspace():
        """Create new workspace"""
        data = request.get_json()

        if not data or 'name' not in data or 'type' not in data:
            return jsonify({'success': False, 'message': 'Missing required fields: name and type'}), 400

        if not data['name'].strip():
            return jsonify({'success': False, 'message': 'Workspace name cannot be empty'}), 400

        conn = db_manager.get_connection()
        c = conn.cursor()

        try:
            c.execute(
                '''INSERT INTO workspaces (user_id, name, type, description)
                        VALUES (?, ?, ?, ?)''',
                (current_user.id, data['name'].strip(), data['type'], data.get('description', '')),
            )

            workspace_id = c.lastrowid
            conn.commit()

            return jsonify({'success': True, 'workspace_id': workspace_id, 'message': 'Workspace created successfully'})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'message': str(e)}), 400
        finally:
            conn.close()

    @app.route('/api/scenarios', methods=['GET'])
    @login_required
    def get_scenarios():
        try:
            scenarios = db.get_scenarios(current_user.id)
            return jsonify({'success': True, 'scenarios': scenarios})
        except Exception as e:
            print(f"Error in get_scenarios: {e}")
            import traceback

            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/scenarios/<int:scenario_id>', methods=['GET'])
    @login_required
    def get_scenario(scenario_id):
        try:
            scenario = db.get_scenario(scenario_id, current_user.id)
            if scenario:
                return jsonify({'success': True, 'scenario': scenario})
            return jsonify({'success': False, 'message': 'Scenario not found'}), 404
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/scenarios', methods=['POST'])
    @login_required
    def create_scenario():
        try:
            data = request.get_json()
            print(f"Creating scenario for user {current_user.id}: {data.get('name')}")
            scenario_id = db.create_scenario(
                user_id=current_user.id,
                name=data.get('name'),
                description=data.get('description', ''),
                active=data.get('active', False),
                steps=data.get('steps'),
            )
            return jsonify({'success': True, 'message': 'Scenario created successfully', 'id': scenario_id})
        except Exception as e:
            print(f"Error in create_scenario: {e}")
            import traceback

            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/scenarios/<int:scenario_id>', methods=['PUT'])
    @login_required
    def update_scenario(scenario_id):
        try:
            data = request.get_json()
            db.update_scenario(scenario_id, current_user.id, data)
            return jsonify({'success': True, 'message': 'Scenario updated successfully'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/scenarios/<int:scenario_id>', methods=['DELETE'])
    @login_required
    def delete_scenario(scenario_id):
        try:
            db.delete_scenario(scenario_id, current_user.id)
            return jsonify({'success': True, 'message': 'Scenario deleted successfully'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500