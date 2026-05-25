"""Page-rendering routes — page_bp Blueprint."""
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from core.config import Config
from core.extensions import db_manager
from core.logger import get_logger

logger = get_logger(__name__)

page_bp = Blueprint('pages', __name__)


def _settings_config():
    return {
        'store': {
            'title': 'Store Profile',
            'description': 'Manage store identity, address, and currency.',
            'icon': 'fa-store',
            'gradient': 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
            'links': [],
        },
        'appearance': {
            'title': 'Appearance',
            'description': 'Customize workspace theme and layout.',
            'icon': 'fa-palette',
            'gradient': 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
            'links': [],
        },
        'system': {
            'title': 'System & Backup',
            'description': 'Database backups, storage management, and maintenance.',
            'icon': 'fa-server',
            'gradient': 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%)',
            'links': [],
        },
    }


@page_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('pages.workspace'))
    return render_template('signin.html')


@page_bp.route('/admin')
@login_required
def admin_dashboard():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('pages.workspace'))
    db_type = 'PostgreSQL' if getattr(Config, 'USE_POSTGRES', False) else 'SQLite'
    return render_template('admin_dashboard.html', user=current_user, db_type=db_type)


@page_bp.route('/admin/workspace')
@login_required
def admin_workspace():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('pages.workspace'))
    return redirect(url_for('pages.admin_dashboard'))


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
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM system_settings')
            for row in cursor.fetchall():
                all_settings[row['key']] = row['value']
    except Exception as e:
        logger.error("Error fetching settings: %s", e, exc_info=True)
    return render_template('settings.html', user=current_user, settings_sections=config, all_settings=all_settings)


@page_bp.route('/manager/create-user')
@login_required
def create_user_account():
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('pages.workspace'))
    return render_template('create_user_account.html', user=current_user)


@page_bp.route('/admin/managers')
@login_required
def admin_managers():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('pages.workspace'))
    return render_template('admin_managers.html', user=current_user)


@page_bp.route('/admin/roles')
@login_required
def admin_roles():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('pages.workspace'))
    return render_template('admin_roles.html', user=current_user)


@page_bp.route('/admin/analytics')
@login_required
def admin_analytics():
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('pages.workspace'))
    return render_template('admin_analytics.html', user=current_user, analytics_data=None)


@page_bp.route('/admin/subscriptions')
@login_required
def admin_subscriptions():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('pages.workspace'))
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
@login_required
def se_reports():
    return render_template('se_reports.html', user=current_user)


@page_bp.route('/scenarios')
@login_required
def scenarios():
    return render_template('scenarios.html', user=current_user)


@page_bp.route('/workspace/builder')
@login_required
def workspace_builder():
    return render_template('workspace_builder.html', user=current_user)
