"""Internal endpoint backing Gateway's team-only cross-app admin page —
aggregates this app's own numbers so Gateway doesn't touch this app's DB
directly. Not for shop-owner customers, never wired into any UI here.
"""
import hmac
import logging

from flask import Blueprint, jsonify, request

from core.config import Config
from core.sanxuat_db import get_connection
from core.auth_db import count_managers

logger = logging.getLogger(__name__)

internal_admin_bp = Blueprint('internal_admin', __name__)

_ACTIVE_STATUSES = ('draft', 'pending_approval', 'approved', 'in_progress')


def _authorized(req):
    expected = Config.PLATFORM_STATS_TOKEN
    provided = req.headers.get('X-Platform-Token', '')
    return bool(expected) and hmac.compare_digest(provided, expected)


@internal_admin_bp.route('/api/internal/platform-stats', methods=['GET'])
def platform_stats():
    if not _authorized(request):
        return jsonify({'success': False, 'error': 'unauthorized'}), 401

    try:
        manager_accounts = count_managers()

        conn = get_connection()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) AS cnt FROM production_orders')
        total_orders = c.fetchone()['cnt'] or 0
        placeholders = ', '.join(['?'] * len(_ACTIVE_STATUSES))
        c.execute(
            f'SELECT COUNT(*) AS cnt FROM production_orders WHERE status IN ({placeholders})',
            _ACTIVE_STATUSES,
        )
        active_orders = c.fetchone()['cnt'] or 0
        c.execute("SELECT COUNT(*) AS cnt FROM production_orders WHERE status = 'completed'")
        completed_orders = c.fetchone()['cnt'] or 0
        conn.close()

        return jsonify({
            'success': True,
            'app': 'san_xuat',
            'manager_accounts': manager_accounts,
            'production_orders_total': total_orders,
            'production_orders_active': active_orders,
            'production_orders_completed': completed_orders,
        })
    except Exception as exc:
        logger.error('[internal-admin] platform-stats failed: %s', exc, exc_info=True)
        return jsonify({'success': False, 'error': str(exc)}), 500
