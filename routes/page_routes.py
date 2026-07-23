"""Page-rendering routes — page_bp Blueprint."""
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from core.config import Config
from core.extensions import db_manager
from core.logger import get_logger
from core.security import require_role

logger = get_logger(__name__)

page_bp = Blueprint('pages', __name__)


def _settings_config():
    return {
        'store': {
            'title': 'Hồ sơ cửa hàng',
            'description': 'Quản lý tên, địa chỉ và đơn vị tiền tệ của cửa hàng.',
            'icon': 'fa-store',
            'gradient': 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
            'links': [],
            'i18n_key': 'store',
        },
        'appearance': {
            'title': 'Giao diện',
            'description': 'Tuỳ chỉnh giao diện và ngôn ngữ hiển thị của không gian làm việc.',
            'icon': 'fa-palette',
            'gradient': 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
            'links': [],
            'i18n_key': 'appearance',
        },
        'system': {
            'title': 'Hệ thống & Sao lưu',
            'description': 'Sao lưu dữ liệu, quản lý lưu trữ và bảo trì hệ thống.',
            'icon': 'fa-server',
            'gradient': 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%)',
            'links': [],
            'i18n_key': 'system',
        },
    }


@page_bp.route('/')
def index():
    # No local landing/choose-area anymore — those live on the Gateway app.
    # You only ever land here already authenticated (Gateway sent you), but
    # handle a stray direct hit gracefully either way.
    if current_user.is_authenticated:
        return redirect(url_for('pages.workspace'))
    return redirect(Config.GATEWAY_ORIGIN)


@page_bp.route('/admin')
@require_role('admin', redirect_to='pages.workspace')
def admin_dashboard():
    db_type = 'PostgreSQL' if getattr(Config, 'USE_POSTGRES', False) else 'SQLite'
    return render_template('admin_dashboard.html', user=current_user, db_type=db_type)


@page_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)


@page_bp.route('/workspace')
@login_required
def workspace():
    return render_template('workspace.html', user=current_user)


@page_bp.route('/settings')
@login_required
def settings():
    config = _settings_config()
    all_settings = {}
    try:
        # `get_business_db_connection` (không phải `get_business_connection`) là
        # @contextmanager — `get_business_connection` trả PGShimConnection, vốn
        # KHÔNG implement __enter__/__exit__, nên `with` ở đây từng ném
        # TypeError lúc load settings.
        with db_manager.get_business_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM system_settings')
            for row in cursor.fetchall():
                all_settings[row['key']] = row['value']
    except Exception as e:
        logger.error("Error fetching settings: %s", e, exc_info=True)
    return render_template('settings.html', user=current_user, settings_sections=config, all_settings=all_settings)


@page_bp.route('/manager/create-user')
@require_role('manager', redirect_to='pages.workspace')
def create_user_account():
    return render_template('create_user_account.html', user=current_user)


@page_bp.route('/admin/managers')
@require_role('admin', redirect_to='pages.workspace')
def admin_managers():
    return render_template('admin_managers.html', user=current_user)


@page_bp.route('/admin/warehouses')
@require_role('admin', redirect_to='pages.workspace')
def admin_warehouses():
    return render_template('admin_warehouses.html', user=current_user)


@page_bp.route('/admin/roles')
@require_role('admin', redirect_to='pages.workspace')
def admin_roles():
    return render_template('admin_roles.html', user=current_user)


@page_bp.route('/admin/analytics')
@require_role('manager', redirect_to='pages.workspace')
def admin_analytics():
    return render_template('admin_analytics.html', user=current_user, analytics_data=None)


@page_bp.route('/admin/subscriptions')
@require_role('admin', redirect_to='pages.workspace')
def admin_subscriptions():
    return render_template('admin_subscriptions.html', user=current_user)


@page_bp.route('/customers')
@login_required
def customers():
    return render_template('customers.html', user=current_user)


@page_bp.route('/products')
@login_required
def products():
    return render_template('products.html', user=current_user)


@page_bp.route('/imports')
@login_required
def imports():
    return render_template('imports.html', user=current_user)


@page_bp.route('/exports')
@login_required
def exports():
    return render_template('exports.html', user=current_user)


@page_bp.route('/se/auto-import')
@login_required
def se_auto_import():
    return render_template('se_auto_import.html', user=current_user)


@page_bp.route('/se/reports')
@require_role('manager', redirect_to='pages.workspace')
def se_reports():
    return render_template('se_reports.html', user=current_user)


@page_bp.route('/scenarios')
@login_required
def scenarios():
    return render_template('scenarios.html', user=current_user)


@page_bp.route('/iot-monitor')
@login_required
def iot_monitor():
    return render_template('iot_monitor.html', user=current_user)
