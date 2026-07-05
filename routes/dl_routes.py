"""Các route proxy cho DL và lịch sử bán hàng sản phẩm, tách ra từ app.py."""

from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required

from core.services.dl_client import DLClient
from core.logger import get_logger
from core.security import safe_api_error, validate_upload

logger = get_logger(__name__)


dl_bp = Blueprint("dl", __name__)

DL_UPLOAD_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
DL_UPLOAD_MIMETYPES = {'image/png', 'image/jpeg', 'image/webp', 'application/pdf'}


@dl_bp.route('/api/dl/detect', methods=['POST'])
@login_required
def api_dl_detect():
    """Proxy tới DL Service để nhận diện hóa đơn."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Chưa tải tệp lên'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Chưa chọn tệp'}), 400
    try:
        validate_upload(file, DL_UPLOAD_EXTENSIONS, DL_UPLOAD_MIMETYPES)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    try:
        client = DLClient()
        file_bytes = file.read()
        result = client.detect_invoice(file_bytes=file_bytes, filename=file.filename)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 500

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return safe_api_error(logger, exc=e)


@dl_bp.route('/api/dl/forecast', methods=['POST'])
@login_required
def api_dl_forecast():
    """Proxy to DL Service for quantity forecasting."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'error': 'Chưa cung cấp dữ liệu'}), 400

    try:
        client = DLClient()
        result = client.forecast_quantity(data)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 500

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return safe_api_error(logger, exc=e)


@dl_bp.route('/api/products/<int:product_id>/sales_history', methods=['GET'])
@login_required
def api_get_product_sales_history(product_id):
    """Lấy chuỗi lịch sử bán hàng của sản phẩm từ chi tiết xuất hàng."""
    conn = None
    try:
        conn = current_app.extensions['database'].get_connection()
        c = conn.cursor()

        c.execute(
            '''
            SELECT d.quantity
            FROM export_details d
            JOIN export_transactions t ON d.export_id = t.id
            WHERE d.product_id = ?
              AND (? = 'admin' OR t.created_by = ?)
            ORDER BY t.created_at DESC
            LIMIT 10
            ''',
            (product_id, getattr(current_user, 'role', 'user'), current_user.id),
        )

        rows = c.fetchall()
        series = [r['quantity'] for r in rows][::-1]

        return jsonify({'success': True, 'series': series})
    except Exception as e:
        return safe_api_error(logger, exc=e)
    finally:
        if conn:
            conn.close()
