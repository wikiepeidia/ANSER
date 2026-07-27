"""Internal endpoint backing Gateway's team-only cross-app admin page —
aggregates this app's own numbers so Gateway doesn't touch this app's DB
directly. Not for shop-owner customers, never wired into any UI here.
"""
import hmac

from flask import Blueprint, current_app, jsonify, request

from core.config import Config
from core.logger import get_logger

logger = get_logger(__name__)

internal_admin_bp = Blueprint('internal_admin', __name__)


def _authorized(req):
    expected = Config.PLATFORM_STATS_TOKEN
    provided = req.headers.get('X-Platform-Token', '')
    return bool(expected) and hmac.compare_digest(provided, expected)


@internal_admin_bp.route('/api/internal/platform-stats', methods=['GET'])
def platform_stats():
    if not _authorized(request):
        return jsonify({'success': False, 'error': 'unauthorized'}), 401

    db = current_app.extensions.get('database')
    if not db:
        return jsonify({'success': False, 'error': 'DB not available'}), 500

    try:
        auth_conn = db.get_connection()
        ac = auth_conn.cursor()
        # Every shop owner signs up with role='manager' (register_user()'s
        # own default) — the closest proxy this data model has today for
        # "how many shops are on the platform," since warehouses/sales
        # aren't yet isolated per manager account (single shared dataset,
        # not true per-tenant isolation — see core/services/*_service.py).
        ac.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'manager'")
        manager_accounts = ac.fetchone()['cnt'] or 0
        auth_conn.close()

        conn = db.get_business_connection()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) AS cnt, COALESCE(SUM(total_amount), 0) AS total FROM sales')
        row = c.fetchone()
        total_orders = row['cnt'] or 0
        total_revenue = float(row['total'] or 0)
        c.execute('SELECT COUNT(*) AS cnt FROM warehouses')
        warehouse_count = c.fetchone()['cnt'] or 0
        conn.close()

        return jsonify({
            'success': True,
            'app': 'retail',
            'manager_accounts': manager_accounts,
            'warehouse_count': warehouse_count,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
        })
    except Exception as exc:
        logger.error('[internal-admin] platform-stats failed: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
