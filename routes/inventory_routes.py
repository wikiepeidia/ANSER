"""Inventory transaction blueprint routes extracted from app.py."""

from flask import Blueprint, jsonify, request
from flask_login import login_required

from core.services import inventory_tx_service
from core.services.service_errors import ServiceInvariantError, ServiceValidationError

inventory_bp = Blueprint("inventory", __name__)


def _app_module():
    """Lazy app module import to avoid circular imports at module load."""
    import app as app_module

    return app_module


@inventory_bp.route('/api/imports', methods=['GET'])
@login_required
def api_get_imports():
    """Get all import transactions."""
    conn = _app_module().db_manager.get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM import_transactions ORDER BY created_at DESC')
    imports = []
    for row in c.fetchall():
        imports.append(
            {
                'id': row[0],
                'code': row[1],
                'supplier_name': row[2],
                'total_amount': row[3],
                'notes': row[4],
                'status': row[5],
                'created_at': row[7],
            }
        )
    conn.close()
    return jsonify({'success': True, 'imports': imports})


@inventory_bp.route('/api/imports', methods=['POST'])
@login_required
def api_create_import():
    """Create a new import transaction."""
    data = request.get_json(silent=True) or {}
    app_module = _app_module()
    conn = app_module.db_manager.get_connection()

    try:
        result = inventory_tx_service.create_import_transaction(conn, app_module.current_user.id, data)
        return jsonify({'success': True, 'message': result['message'], 'id': result['id']})
    except ServiceValidationError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except ServiceInvariantError as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@inventory_bp.route('/api/imports/<int:import_id>', methods=['GET'])
@login_required
def api_get_import_details(import_id):
    """Get import transaction details."""
    conn = _app_module().db_manager.get_connection()

    try:
        result = inventory_tx_service.get_import_transaction_details(conn, import_id)
        if not result:
            return jsonify({'success': False, 'message': 'Import not found'}), 404
        return jsonify(
            {
                'success': True,
                'transaction': result['transaction'],
                'details': result['details'],
            }
        )
    except ServiceInvariantError as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@inventory_bp.route('/api/exports', methods=['GET'])
@login_required
def api_get_exports():
    """Get all export transactions."""
    conn = _app_module().db_manager.get_connection()
    c = conn.cursor()
    c.execute(
        '''SELECT e.*, c.name as customer_name FROM export_transactions e
                 LEFT JOIN customers c ON e.customer_id = c.id
                 ORDER BY e.created_at DESC'''
    )
    exports = []
    for row in c.fetchall():
        exports.append(
            {
                'id': row[0],
                'code': row[1],
                'customer_id': row[2],
                'total_amount': row[3],
                'notes': row[4],
                'status': row[5],
                'created_at': row[7],
                'customer_name': row[8] if len(row) > 8 else '',
            }
        )
    conn.close()
    return jsonify({'success': True, 'exports': exports})


@inventory_bp.route('/api/exports', methods=['POST'])
@login_required
def api_create_export():
    """Create a new export transaction."""
    data = request.get_json(silent=True) or {}
    app_module = _app_module()
    conn = app_module.db_manager.get_connection()

    try:
        result = inventory_tx_service.create_export_transaction(
            conn,
            app_module.current_user.id,
            data,
            app_module.automation_engine,
        )
        return jsonify({'success': True, 'message': result['message'], 'id': result['id']})
    except ServiceValidationError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except ServiceInvariantError as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@inventory_bp.route('/api/exports/<int:export_id>', methods=['GET'])
@login_required
def api_get_export_details(export_id):
    """Get export transaction details."""
    conn = _app_module().db_manager.get_connection()

    try:
        result = inventory_tx_service.get_export_transaction_details(conn, export_id)
        if not result:
            return jsonify({'success': False, 'message': 'Export not found'}), 404
        return jsonify(
            {
                'success': True,
                'transaction': result['transaction'],
                'details': result['details'],
            }
        )
    except ServiceInvariantError as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()
