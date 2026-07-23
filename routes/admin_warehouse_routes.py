"""Warehouse config CRUD — per-warehouse low-stock alert settings.

Config-only: does not track real per-warehouse stock. Each warehouse row is
an independent alert profile (threshold + Discord webhook) that the
low_stock_alert n8n workflow loops over via /api/n8n/internal/warehouses.
"""
from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from core.security import require_role

admin_warehouse_bp = Blueprint('admin_warehouses', __name__)


@admin_warehouse_bp.route('/api/admin/warehouses', methods=['GET'])
@require_role('manager')
def list_warehouses():
    conn = current_app.extensions['database'].get_business_connection()
    c = conn.cursor()
    c.execute(
        'SELECT id, name, low_stock_threshold, discord_webhook_url, notification_email,'
        ' is_active, created_at FROM warehouses ORDER BY created_at DESC'
    )
    warehouses = [
        {
            'id': r['id'], 'name': r['name'],
            'low_stock_threshold': r['low_stock_threshold'],
            'discord_webhook_url': r['discord_webhook_url'],
            'notification_email': r['notification_email'],
            'is_active': bool(r['is_active']),
            'created_at': r['created_at'],
        }
        for r in c.fetchall()
    ]
    conn.close()
    return jsonify({'success': True, 'warehouses': warehouses})


@admin_warehouse_bp.route('/api/admin/warehouses', methods=['POST'])
@require_role('manager')
def create_warehouse():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Thiếu tên kho'}), 400
    threshold = data.get('low_stock_threshold', 10)
    discord_webhook_url = (data.get('discord_webhook_url') or '').strip()
    notification_email = (data.get('notification_email') or '').strip()

    conn = current_app.extensions['database'].get_business_connection()
    c = conn.cursor()
    c.execute(
        '''INSERT INTO warehouses (name, low_stock_threshold, discord_webhook_url, notification_email, created_by)
           VALUES (?, ?, ?, ?, ?)''',
        (name, threshold, discord_webhook_url or None, notification_email or None, current_user.id),
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Tạo kho thành công'})


@admin_warehouse_bp.route('/api/admin/warehouses/<int:warehouse_id>/update', methods=['POST'])
@require_role('manager')
def update_warehouse(warehouse_id):
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Thiếu tên kho'}), 400
    threshold = data.get('low_stock_threshold', 10)
    discord_webhook_url = (data.get('discord_webhook_url') or '').strip()
    notification_email = (data.get('notification_email') or '').strip()
    is_active = 1 if data.get('is_active', True) else 0

    conn = current_app.extensions['database'].get_business_connection()
    c = conn.cursor()
    c.execute(
        '''UPDATE warehouses SET name=?, low_stock_threshold=?, discord_webhook_url=?,
           notification_email=?, is_active=? WHERE id=?''',
        (name, threshold, discord_webhook_url or None, notification_email or None, is_active, warehouse_id),
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Cập nhật kho thành công'})


@admin_warehouse_bp.route('/api/admin/warehouses/<int:warehouse_id>/delete', methods=['POST'])
@require_role('manager')
def delete_warehouse(warehouse_id):
    conn = current_app.extensions['database'].get_business_connection()
    c = conn.cursor()
    c.execute('DELETE FROM warehouses WHERE id=?', (warehouse_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Xóa kho thành công'})
