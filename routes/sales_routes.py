"""Sales and POS routes — sales_bp Blueprint."""
import json
import os

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required

from core.services.sales_service import create_sale, delete_sale, get_sales_history
from core.logger import get_logger

logger = get_logger(__name__)

sales_bp = Blueprint('sales', __name__)


@sales_bp.route('/sale')
@login_required
def sale_page():
    return render_template('sale.html')


@sales_bp.route('/api/products/search')
@login_required
def search_products():
    query = request.args.get('q', '').lower()
    random_mode = request.args.get('random') == 'true'
    try:
        catalog_path = os.path.join(current_app.root_path, 'dl_service/data/product_catalogs.json')
        if not os.path.exists(catalog_path):
            catalog_path = os.path.join(os.getcwd(), 'dl_service/data/product_catalogs.json')
        with open(catalog_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        if random_mode:
            import random
            results = random.sample(products, min(len(products), 8))
        else:
            results = [
                p for p in products
                if query in p.get('name', '').lower() or query in str(p.get('id', '')).lower()
            ][:5]
        return jsonify(results)
    except Exception as e:
        logger.error("Error searching products: %s", e, exc_info=True)
        return jsonify([])


@sales_bp.route('/api/sales/create', methods=['POST'])
@login_required
def api_create_sale():
    data = request.json or {}
    try:
        create_sale(
            current_user.id, data.get('total_amount'), data.get('amount_given'),
            data.get('change_amount'), data.get('items', []),
            data.get('payment_method', 'cash'), data.get('workspace_id'),
            data.get('category', 'Retail'),
        )
        return jsonify({'success': True, 'message': 'Ghi lại giao dịch thành công'})
    except Exception as e:
        logger.error("Error creating sale for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500


@sales_bp.route('/api/sales/history', methods=['GET'])
@login_required
def api_get_sales_history():
    search_query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    try:
        history = get_sales_history(current_user.id, search_query, limit)
        return jsonify(history)
    except Exception as e:
        logger.error("Error fetching sales history for user %s: %s", current_user.id, e, exc_info=True)
        return jsonify({'error': str(e)}), 500


@sales_bp.route('/api/sales/history/<int:sale_id>', methods=['DELETE'])
@login_required
def api_delete_sale(sale_id):
    try:
        delete_sale(sale_id)
        return jsonify({'success': True, 'message': 'Xóa giao dịch thành công'})
    except LookupError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        logger.error("Error deleting sale %s: %s", sale_id, e, exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500
