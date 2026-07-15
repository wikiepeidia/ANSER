"""Dev page routes — bypass auth for local testing."""
from flask import Blueprint, render_template

page_bp = Blueprint('pages', __name__)

@page_bp.route('/')
def home():
    return render_template('base.html', user={'email': 'dev@local'}, gateway_origin='http://127.0.0.1:5000')

@page_bp.route('/health')
def health():
    return {'status': 'ok', 'service': 'san-xuat'}
