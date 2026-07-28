"""Page routes — landing + choose-area. Both mảng (Bán lẻ, Sản xuất) are
separate apps now; this only ever links out to them, never renders them."""
from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_required

from core.config import Config
from core.security import require_internal_admin

page_bp = Blueprint('pages', __name__)

_ORIGINS = {'retail': Config.RETAIL_ORIGIN, 'san_xuat': Config.SANXUAT_ORIGIN}


@page_bp.route('/')
def index():
    if current_user.is_authenticated:
        area = session.get('active_area')
        if area in _ORIGINS:
            return redirect(_ORIGINS[area])
        return redirect(url_for('pages.choose_area'))
    return render_template('landing.html')


@page_bp.route('/landing')
def landing():
    return render_template('landing.html')


@page_bp.route('/choose-area')
@login_required
def choose_area():
    email = (getattr(current_user, 'email', '') or '').strip().lower()
    return render_template(
        'choose_area.html', user=current_user,
        retail_origin=Config.RETAIL_ORIGIN, sanxuat_origin=Config.SANXUAT_ORIGIN,
        is_internal_admin=email in Config.INTERNAL_ADMIN_EMAILS,
    )


@page_bp.route('/choose-area/<area>')
@login_required
def set_active_area(area):
    if area not in _ORIGINS:
        flash('Mảng không hợp lệ', 'error')
        return redirect(url_for('pages.choose_area'))
    session['active_area'] = area
    return redirect(_ORIGINS[area])


@page_bp.route('/internal-admin-dashboard')
@require_internal_admin(redirect_to='pages.choose_area')
def internal_admin_dashboard():
    return render_template('internal_admin_dashboard.html', user=current_user)
