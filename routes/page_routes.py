"""Page routes — serves the San Xuat dashboard shell."""
from flask import Blueprint, render_template, redirect
from flask_login import current_user, login_required

from core.config import Config

page_bp = Blueprint('pages', __name__)


@page_bp.route('/')
@login_required
def home():
    return render_template('base.html', user=current_user, gateway_origin=Config.GATEWAY_ORIGIN)


@page_bp.route('/health')
def health():
    return {'status': 'ok', 'service': 'san-xuat'}
