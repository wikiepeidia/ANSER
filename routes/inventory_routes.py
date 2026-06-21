"""Inventory transaction blueprint routes extracted from app.py."""

from flask import Blueprint, jsonify, request, send_file, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from core.services import inventory_tx_service
from core.services.service_errors import ServiceInvariantError, ServiceValidationError
from core.excel_parser import ExcelParser
from core.logger import get_logger

logger = get_logger(__name__)

inventory_bp = Blueprint("inventory", __name__)


def _notify_n8n_order(order_type, data, user_email):
    """Fire-and-forget: notify n8n when import/export is created."""
    import os
    import threading
    import requests

    discord_url = os.environ.get('DISCORD_WEBHOOK_URL', '')
    if not discord_url:
        return

    def _send():
        try:
            payload = {
                'type': order_type,
                'items': data.get('items', []),
                'notes': data.get('notes', ''),
                'user': user_email,
                'discord_url': discord_url,
            }
            requests.post('http://localhost:5678/webhook/new-order',
                          json=payload, timeout=10)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


@inventory_bp.route('/api/imports', methods=['GET'])
@login_required
def api_get_imports():
    """Get all import transactions."""
    conn = current_app.extensions['database'].get_connection()
    c = conn.cursor()
    c.execute(
        'SELECT id, code, supplier_name, total_amount, notes, status, created_by, created_at'
        ' FROM import_transactions ORDER BY created_at DESC'
    )
    imports = []
    for row in c.fetchall():
        imports.append(
            {
                'id': row['id'],
                'code': row['code'],
                'supplier_name': row['supplier_name'],
                'total_amount': row['total_amount'],
                'notes': row['notes'],
                'status': row['status'],
                'created_at': row['created_at'],
            }
        )
    conn.close()
    return jsonify({'success': True, 'imports': imports})


@inventory_bp.route('/api/imports', methods=['POST'])
@login_required
def api_create_import():
    """Create a new import transaction."""
    data = request.get_json(silent=True) or {}
    conn = current_app.extensions['database'].get_connection()

    try:
        result = inventory_tx_service.create_import_transaction(conn, current_user.id, data)
        _notify_n8n_order('import', data, current_user.email)
        return jsonify({
            'success': True,
            'message': result['message'],
            'id': result['id'],
            'products_updated': result.get('products_updated', 0),
            'products_created': result.get('products_created', 0),
        })
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
    conn = current_app.extensions['database'].get_connection()

    try:
        result = inventory_tx_service.get_import_transaction_details(conn, import_id)
        if not result:
            return jsonify({'success': False, 'message': 'Không tìm thấy phiếu nhập'}), 404
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


@inventory_bp.route('/api/imports/upload/excel', methods=['POST'])
@login_required
def api_upload_excel_import():
    """Upload Excel file to parse import data."""
    try:
        # Check if file is provided
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Validate file type
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'success': False, 'error': 'Invalid file type. Please upload Excel file (.xlsx or .xls)'}), 400
        
        # Read file content
        file_content = file.read()
        
        # Parse Excel file
        result = ExcelParser.parse_import_file(file_content)
        
        if not result['success']:
            return jsonify({'success': False, 'error': result.get('error', 'Failed to parse Excel file')}), 400
        
        logger.info(f"User {current_user.id} uploaded Excel file with {result['row_count']} items")
        
        return jsonify({
            'success': True,
            'message': f'Successfully parsed {result["row_count"]} items from Excel file',
            'items': result['items'],
            'warnings': result.get('warnings', [])
        })
        
    except Exception as e:
        logger.error(f"Error uploading Excel import file: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/imports/download/template', methods=['GET'])
@login_required
def api_download_import_template():
    """Download Excel template for import."""
    try:
        template_bytes = ExcelParser.get_sample_template()
        from io import BytesIO
        return send_file(
            BytesIO(template_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='Import_Template.xlsx'
        )
    except Exception as e:
        logger.error(f"Error generating import template: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@inventory_bp.route('/api/exports', methods=['GET'])
@login_required
def api_get_exports():
    """Get all export transactions."""
    conn = current_app.extensions['database'].get_connection()
    c = conn.cursor()
    c.execute(
        'SELECT e.id, e.code, e.customer_id, e.total_amount, e.notes, e.status,'
        ' e.created_by, e.created_at, c.name AS customer_name'
        ' FROM export_transactions e'
        ' LEFT JOIN customers c ON e.customer_id = c.id'
        ' ORDER BY e.created_at DESC'
    )
    exports = []
    for row in c.fetchall():
        exports.append(
            {
                'id': row['id'],
                'code': row['code'],
                'customer_id': row['customer_id'],
                'total_amount': row['total_amount'],
                'notes': row['notes'],
                'status': row['status'],
                'created_at': row['created_at'],
                'customer_name': row['customer_name'] or '',
            }
        )
    conn.close()
    return jsonify({'success': True, 'exports': exports})


@inventory_bp.route('/api/exports', methods=['POST'])
@login_required
def api_create_export():
    """Create a new export transaction."""
    data = request.get_json(silent=True) or {}
    conn = current_app.extensions['database'].get_connection()

    try:
        result = inventory_tx_service.create_export_transaction(
            conn,
            current_user.id,
            data,
            current_app.extensions['automation_engine'],
        )
        _notify_n8n_order('export', data, current_user.email)
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
    conn = current_app.extensions['database'].get_connection()

    try:
        result = inventory_tx_service.get_export_transaction_details(conn, export_id)
        if not result:
            return jsonify({'success': False, 'message': 'Không tìm thấy phiếu xuất'}), 404
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
