"""DL proxy and product-sales-history routes extracted from app.py."""

from flask import Blueprint, jsonify, request
from flask_login import login_required

from core.services.dl_client import DLClient


dl_bp = Blueprint("dl", __name__)


def _app_module():
    """Lazy app module import to avoid circular imports at module load."""
    import app as app_module

    return app_module


@dl_bp.route('/api/dl/detect', methods=['POST'])
@login_required
def api_dl_detect():
    """Proxy to DL Service for invoice detection."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400

    try:
        client = DLClient()
        file_bytes = file.read()
        result = client.detect_invoice(file_bytes=file_bytes, filename=file.filename)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 500

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        print(f"DL Proxy Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dl_bp.route('/api/dl/forecast', methods=['POST'])
@login_required
def api_dl_forecast():
    """Proxy to DL Service for quantity forecasting."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    try:
        client = DLClient()
        result = client.forecast_quantity(data)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 500

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        print(f"DL Proxy Error (Forecast): {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@dl_bp.route('/api/products/<int:product_id>/sales_history', methods=['GET'])
@login_required
def api_get_product_sales_history(product_id):
    """Get sales history series for a product from export details."""
    conn = None
    try:
        conn = _app_module().db_manager.get_connection()
        c = conn.cursor()

        c.execute(
            '''
            SELECT d.quantity
            FROM export_details d
            JOIN export_transactions t ON d.export_id = t.id
            WHERE d.product_id = ?
            ORDER BY t.created_at DESC
            LIMIT 10
            ''',
            (product_id,),
        )

        rows = c.fetchall()
        series = [r[0] for r in rows][::-1]

        return jsonify({'success': True, 'series': series})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if conn:
            conn.close()
