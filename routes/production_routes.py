"""Production order routes — real backend for orders CRUD + status transitions.

Replaces the localStorage mock in static/js/store.js (Production Orders
section). See .planning/phases/01-production-orders-bom-foundation/
01-CONTEXT.md for the locked 6-state transition contract this file
implements as the single server-side source of truth.
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.sanxuat_db import get_connection, now

production_bp = Blueprint('production', __name__)


def _serialize_order(row):
    return {
        'id': row['id'],
        'code': row['code'],
        'productCode': row['product_code'],
        'productName': row['product_name'],
        'quantity': row['quantity'],
        'unit': row['unit'],
        'customerName': row['customer_name'] or '',
        'notes': row['notes'] or '',
        'status': row['status'],
        'createdAt': row['created_at'],
        'createdBy': row['created_by'],
        'approvedAt': row['approved_at'],
        'approvedBy': row['approved_by'],
    }


# ── Production Orders CRUD (PROD-01, PROD-03) ───────────────────────────

@production_bp.route('/api/production-orders', methods=['GET'])
@login_required
def get_production_orders():
    status = request.args.get('status')
    conn = get_connection()
    try:
        if status:
            rows = conn.execute(
                'SELECT * FROM production_orders WHERE is_deleted = 0 AND status = ? '
                'ORDER BY created_at DESC',
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM production_orders WHERE is_deleted = 0 ORDER BY created_at DESC'
            ).fetchall()
        return jsonify({'success': True, 'orders': [_serialize_order(r) for r in rows]})
    finally:
        conn.close()


@production_bp.route('/api/production-orders', methods=['POST'])
@login_required
def create_production_order():
    data = request.get_json(silent=True) or {}
    if not data.get('productCode') or not data.get('productName'):
        return jsonify({'success': False, 'message': 'Thiếu mã sản phẩm hoặc tên sản phẩm'}), 400
    try:
        quantity = float(data.get('quantity') or 0)
    except (TypeError, ValueError):
        quantity = 0
    if quantity <= 0:
        return jsonify({'success': False, 'message': 'Số lượng phải lớn hơn 0'}), 400

    conn = get_connection()
    try:
        cur = conn.execute(
            'INSERT INTO production_orders (product_code, product_name, quantity, unit, '
            'customer_name, notes, status, created_by, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (data['productCode'], data['productName'], quantity, data.get('unit', 'cái'),
             data.get('customerName', ''), data.get('notes', ''), 'draft', current_user.id, now()),
        )
        order_id = cur.lastrowid
        code = f'DH-{1000 + order_id}'
        conn.execute('UPDATE production_orders SET code = ? WHERE id = ?', (code, order_id))
        conn.commit()
        return jsonify({'success': True, 'id': order_id, 'code': code})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@production_bp.route('/api/production-orders/<int:order_id>', methods=['PUT'])
@login_required
def update_production_order(order_id):
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM production_orders WHERE id = ? AND is_deleted = 0', (order_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng'}), 404
        # `status` is intentionally never read from `data` here — only
        # POST .../transition may change status (see Pitfall 1, 01-RESEARCH.md).
        conn.execute(
            'UPDATE production_orders SET product_code=?, product_name=?, quantity=?, unit=?, '
            'customer_name=?, notes=? WHERE id=?',
            (data.get('productCode'), data.get('productName'), data.get('quantity'),
             data.get('unit', 'cái'), data.get('customerName', ''), data.get('notes', ''), order_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Cập nhật đơn hàng thành công'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@production_bp.route('/api/production-orders/<int:order_id>', methods=['DELETE'])
@login_required
def delete_production_order(order_id):
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM production_orders WHERE id = ? AND is_deleted = 0', (order_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng'}), 404
        conn.execute(
            'UPDATE production_orders SET is_deleted = 1, deleted_at = ? WHERE id = ?',
            (now(), order_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Xóa đơn hàng thành công'})
    finally:
        conn.close()
