"""Warehouse config CRUD — per-warehouse low-stock alert settings.

Config-only: does not track real per-warehouse stock. Each warehouse row is
an independent alert profile (threshold + Discord webhook) that the
low_stock_alert n8n workflow loops over via /api/n8n/internal/warehouses.
"""
from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

admin_warehouse_bp = Blueprint('admin_warehouses', __name__)


def _forbidden():
    return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403


@admin_warehouse_bp.route('/api/admin/warehouses', methods=['GET'])
@login_required
def list_warehouses():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return _forbidden()
    conn = current_app.extensions['database'].get_connection()
    c = conn.cursor()
    c.execute(
        'SELECT id, name, low_stock_threshold, discord_webhook_url, is_active, created_at'
        ' FROM warehouses ORDER BY created_at DESC'
    )
    warehouses = [
        {
            'id': r['id'], 'name': r['name'],
            'low_stock_threshold': r['low_stock_threshold'],
            'discord_webhook_url': r['discord_webhook_url'],
            'is_active': bool(r['is_active']),
            'created_at': r['created_at'],
        }
        for r in c.fetchall()
    ]
    conn.close()
    return jsonify({'success': True, 'warehouses': warehouses})


@admin_warehouse_bp.route('/api/admin/warehouses', methods=['POST'])
@login_required
def create_warehouse():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return _forbidden()
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Thiếu tên kho'}), 400
    threshold = data.get('low_stock_threshold', 10)
    discord_webhook_url = (data.get('discord_webhook_url') or '').strip()

    conn = current_app.extensions['database'].get_connection()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO warehouses (name, low_stock_threshold, discord_webhook_url, created_by)
           VALUES (?, ?, ?, ?)''',
        (name, threshold, discord_webhook_url or None, current_user.id),
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Tạo kho thành công'})


@admin_warehouse_bp.route('/api/admin/warehouses/<int:warehouse_id>/update', methods=['POST'])
@login_required
def update_warehouse(warehouse_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return _forbidden()
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Thiếu tên kho'}), 400
    threshold = data.get('low_stock_threshold', 10)
    discord_webhook_url = (data.get('discord_webhook_url') or '').strip()
    is_active = 1 if data.get('is_active', True) else 0

    conn = current_app.extensions['database'].get_connection()
    c = conn.cursor()
    c.execute(
        '''UPDATE warehouses SET name=?, low_stock_threshold=?, discord_webhook_url=?, is_active=?
           WHERE id=?''',
        (name, threshold, discord_webhook_url or None, is_active, warehouse_id),
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Cập nhật kho thành công'})


@admin_warehouse_bp.route('/api/admin/warehouses/<int:warehouse_id>/delete', methods=['POST'])
@login_required
def delete_warehouse(warehouse_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return _forbidden()
    conn = current_app.extensions['database'].get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM warehouses WHERE id=?', (warehouse_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Xóa kho thành công'})
