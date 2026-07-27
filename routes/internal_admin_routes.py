"""Cross-app platform overview — team-only, aggregates Retail + Sản xuất's
own /api/internal/platform-stats into one response. Never exposed to
shop-owner customers; see core/security.py's require_internal_admin.
"""
import logging

import requests

from flask import Blueprint, jsonify

from core.config import Config
from core.security import require_internal_admin

logger = logging.getLogger(__name__)

internal_admin_bp = Blueprint('internal_admin', __name__)

_APPS = {
    'retail': Config.RETAIL_ORIGIN,
    'san_xuat': Config.SANXUAT_ORIGIN,
}


def _fetch(name, origin):
    try:
        r = requests.get(
            f'{origin}/api/internal/platform-stats',
            headers={'X-Platform-Token': Config.PLATFORM_STATS_TOKEN},
            timeout=5,
        )
        if r.status_code != 200:
            return {'success': False, 'error': f'HTTP {r.status_code}'}
        return r.json()
    except requests.RequestException as exc:
        logger.warning('[internal-admin] %s unreachable: %s', name, exc)
        return {'success': False, 'error': 'unreachable'}


@internal_admin_bp.route('/api/internal-admin/platform-stats', methods=['GET'])
@require_internal_admin
def platform_stats():
    # Each app is fetched independently — one being down/unreachable must
    # not take the whole overview page down with it.
    return jsonify({
        'success': True,
        'apps': {name: _fetch(name, origin) for name, origin in _APPS.items()},
    })
