"""Sales and POS routes — sales_bp Blueprint."""
import json
import os

from flask import Blueprint, current_app, jsonify, render_template, request, session
from flask_login import current_user, login_required

from core.services.sales_service import create_sale, delete_sale, get_sales_history
from core.logger import get_logger
from core.security import safe_api_error

logger = get_logger(__name__)

sales_bp = Blueprint('sales', __name__)

# Cache for product catalog
PRODUCT_CATALOG_CACHE = None

_UNUSUAL_MIN_HISTORY = 5     # need this many prior sales before "average" means anything
_UNUSUAL_MULTIPLIER = 3      # flag if new sale > this many times the recent average


def _notify_unusual_transaction(conn, warehouse_id, total_amount, user_email):
    """Fire-and-forget: flag a sale that's a clear outlier vs recent history
    (large-transaction / possible fraud or till error detection) —
    threshold check happens here in Python (cheap, precise SQL aggregate);
    unusual_transaction_alert.json's job is only to format + email once told."""
    import threading
    import requests
    from core.config import Config

    if not warehouse_id or not total_amount:
        return
    try:
        c = conn.cursor()
        # Called right after create_sale() already inserted this exact
        # transaction — COUNT/SUM below include it, so back it out before
        # computing "average of everything BEFORE this sale". Without this,
        # a real outlier drags its own average up and can mask itself,
        # worse the fewer prior transactions there are.
        c.execute(
            'SELECT COUNT(*) AS cnt, COALESCE(SUM(total_amount), 0) AS sum_amount '
            'FROM sales WHERE warehouse_id = ?',
            (warehouse_id,),
        )
        row = c.fetchone()
        count_before = row['cnt'] - 1
        sum_before = float(row['sum_amount'] or 0) - total_amount
    except Exception:
        return
    if count_before < _UNUSUAL_MIN_HISTORY or sum_before <= 0:
        return
    avg_amount = sum_before / count_before
    if avg_amount <= 0 or total_amount <= avg_amount * _UNUSUAL_MULTIPLIER:
        return

    db = current_app.extensions['database']
    wconn = db.get_business_connection()
    try:
        wc = wconn.cursor()
        wc.execute('SELECT notification_email FROM warehouses WHERE id = ?', (warehouse_id,))
        wrow = wc.fetchone()
        email = (wrow['notification_email'] if wrow else '') or ''
    finally:
        wconn.close()
    if not email:
        return

    def _send():
        try:
            requests.post(f'{Config.N8N_ORIGIN}/webhook/unusual-transaction', json={
                'amount': total_amount,
                'average': round(avg_amount, 2),
                'multiplier': round(total_amount / avg_amount, 1),
                'user': user_email,
                'notify_email': email,
            }, timeout=10)
        except Exception:
            pass

    threading.Thread(target=_send, daemon=True).start()


@sales_bp.route('/sale')
@login_required
def sale_page():
    return render_template('sale.html')


@sales_bp.route('/api/products/search')
@login_required
def search_products():
    global PRODUCT_CATALOG_CACHE
    query = request.args.get('q', '').lower()
    random_mode = request.args.get('random') == 'true'
    try:
        if PRODUCT_CATALOG_CACHE is None:
            catalog_path = os.path.join(current_app.root_path, 'dl_service/data/product_catalogs.json')
            if not os.path.exists(catalog_path):
                catalog_path = os.path.join(os.getcwd(), 'dl_service/data/product_catalogs.json')
            
            if os.path.exists(catalog_path):
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    PRODUCT_CATALOG_CACHE = json.load(f)
            else:
                logger.warning("Product catalog file not found: %s", catalog_path)
                PRODUCT_CATALOG_CACHE = []

        products = PRODUCT_CATALOG_CACHE

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
    conn = current_app.extensions['database'].get_business_connection()
    try:
        warehouse_id = session.get('active_warehouse_id')
        create_sale(
            conn, current_user.id, data.get('total_amount'), data.get('amount_given'),
            data.get('change_amount'), data.get('items', []),
            data.get('payment_method', 'cash'), data.get('workspace_id'),
            data.get('category', 'Retail'), warehouse_id,
        )
        _notify_unusual_transaction(conn, warehouse_id, data.get('total_amount'),
                                     getattr(current_user, 'email', ''))
        return jsonify({'success': True, 'message': 'Ghi lại giao dịch thành công'})
    except Exception as e:
        return safe_api_error(logger, exc=e)
    finally:
        conn.close()


@sales_bp.route('/api/sales/history', methods=['GET'])
@login_required
def api_get_sales_history():
    search_query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    conn = current_app.extensions['database'].get_business_connection()
    try:
        history = get_sales_history(conn, current_user.id, search_query, limit,
                                     session.get('active_warehouse_id'))
        return jsonify(history)
    except Exception as e:
        return safe_api_error(logger, exc=e)
    finally:
        conn.close()


@sales_bp.route('/api/sales/history/<int:sale_id>', methods=['DELETE'])
@login_required
def api_delete_sale(sale_id):
    conn = current_app.extensions['database'].get_business_connection()
    try:
        delete_sale(conn, sale_id, current_user.id)
        return jsonify({'success': True, 'message': 'Xóa giao dịch thành công'})
    except LookupError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return safe_api_error(logger, exc=e)
    finally:
        conn.close()
