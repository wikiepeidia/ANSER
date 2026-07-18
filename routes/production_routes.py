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

# Server-side source of truth for the 6-state transition graph — ported
# verbatim from static/js/store.js:202-221 (ORDER_STATUS_FLOW/
# ORDER_STATUS_LABELS/ORDER_TRANSITION_LABELS). Only POST .../transition may
# change `status`; the generic PUT update route never reads it.
ORDER_STATUS_FLOW = {
    'draft': ['pending_approval', 'cancelled'],
    'pending_approval': ['approved', 'draft', 'cancelled'],
    'approved': ['in_progress', 'cancelled'],
    'in_progress': ['completed', 'cancelled'],
    'completed': [],
    'cancelled': [],
}

ORDER_STATUS_LABELS = {
    'draft': 'Nháp',
    'pending_approval': 'Chờ duyệt',
    'approved': 'Đã duyệt',
    'in_progress': 'Đang sản xuất',
    'completed': 'Hoàn thành',
    'cancelled': 'Đã huỷ',
}

ORDER_TRANSITION_LABELS = {
    'draft>pending_approval': 'Gửi duyệt',
    'pending_approval>approved': 'Duyệt đơn',
    'pending_approval>draft': 'Trả về nháp',
    'approved>in_progress': 'Bắt đầu sản xuất',
    'in_progress>completed': 'Hoàn thành',
    'draft>cancelled': 'Huỷ đơn',
    'pending_approval>cancelled': 'Huỷ đơn',
    'approved>cancelled': 'Huỷ đơn',
    'in_progress>cancelled': 'Huỷ đơn',
}


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


def _serialize_event(row):
    return {
        'id': row['id'],
        'orderId': row['order_id'],
        'ts': row['created_at'],
        'event': row['event'],
        'note': row['note'] or '',
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
                'SELECT * FROM production_orders WHERE is_deleted = FALSE AND status = ? '
                'ORDER BY created_at DESC',
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM production_orders WHERE is_deleted = FALSE ORDER BY created_at DESC'
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
        conn.execute(
            'INSERT INTO production_order_events (order_id, event, note, created_at) '
            'VALUES (?, ?, ?, ?)',
            (order_id, 'Tạo đơn hàng', f'Đơn {code} được tạo', now()),
        )
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
            'SELECT id FROM production_orders WHERE id = ? AND is_deleted = FALSE', (order_id,)
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
            'SELECT id FROM production_orders WHERE id = ? AND is_deleted = FALSE', (order_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng'}), 404
        conn.execute(
            'UPDATE production_orders SET is_deleted = TRUE, deleted_at = ? WHERE id = ?',
            (now(), order_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Xóa đơn hàng thành công'})
    finally:
        conn.close()


# ── Status transition + events timeline (PROD-02) ───────────────────────

@production_bp.route('/api/production-orders/<int:order_id>/transition', methods=['POST'])
@login_required
def transition_order(order_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    note = data.get('note') or ''

    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT * FROM production_orders WHERE id = ? AND is_deleted = FALSE', (order_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng'}), 404

        old_status = row['status']
        allowed = ORDER_STATUS_FLOW.get(old_status, [])
        if new_status not in allowed:
            old_label = ORDER_STATUS_LABELS.get(old_status, old_status)
            new_label = ORDER_STATUS_LABELS.get(new_status, new_status)
            return jsonify({
                'success': False,
                'message': f'Không thể chuyển từ "{old_label}" sang "{new_label}"',
            }), 409

        if new_status == 'approved':
            conn.execute(
                'UPDATE production_orders SET status = ?, approved_at = ?, approved_by = ? WHERE id = ?',
                (new_status, now(), current_user.id, order_id),
            )
        else:
            conn.execute(
                'UPDATE production_orders SET status = ? WHERE id = ?',
                (new_status, order_id),
            )

        event_label = ORDER_TRANSITION_LABELS.get(f'{old_status}>{new_status}', 'Chuyển trạng thái')
        conn.execute(
            'INSERT INTO production_order_events (order_id, event, note, created_at) '
            'VALUES (?, ?, ?, ?)',
            (order_id, event_label, note, now()),
        )

        if new_status == 'completed':
            product = conn.execute(
                'SELECT id, stock_quantity, name FROM products WHERE code = ?',
                (row['product_code'],),
            ).fetchone()
            if product:
                conn.execute(
                    'UPDATE products SET stock_quantity = stock_quantity + ?, updated_at = ? WHERE id = ?',
                    (row['quantity'], now(), product['id']),
                )
                stock_note = f"Nhập {row['quantity']} {row['unit']} vào tồn kho \"{product['name']}\""
                conn.execute(
                    'INSERT INTO production_order_events (order_id, event, note, created_at) '
                    'VALUES (?, ?, ?, ?)',
                    (order_id, 'Nhập kho thành phẩm', stock_note, now()),
                )
            # No matching product row: lenient no-op per 01-RESEARCH.md
            # Pitfall 4 / Open Question 2 — order still completes.

        conn.commit()
        return jsonify({'success': True, 'message': 'Cập nhật trạng thái thành công'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@production_bp.route('/api/production-orders/<int:order_id>/events', methods=['GET'])
@login_required
def get_order_events(order_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM production_order_events WHERE order_id = ? ORDER BY created_at ASC',
            (order_id,),
        ).fetchall()
        return jsonify({'success': True, 'events': [_serialize_event(r) for r in rows]})
    finally:
        conn.close()


@production_bp.route('/api/production-orders/events', methods=['GET'])
@login_required
def get_all_order_events():
    order_id = request.args.get('orderId', type=int)
    conn = get_connection()
    try:
        if order_id:
            rows = conn.execute(
                'SELECT * FROM production_order_events WHERE order_id = ? ORDER BY created_at ASC',
                (order_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                'SELECT * FROM production_order_events ORDER BY created_at ASC'
            ).fetchall()
        return jsonify({'success': True, 'events': [_serialize_event(r) for r in rows]})
    finally:
        conn.close()


# ── BOM (bill of materials) — full-replace management + calculate ───────
# (PROD-04, PROD-05). Master data keyed by product_code, decoupled from any
# specific order. See 01-RESEARCH.md Pattern 4 (full-replace, not per-row
# upsert) and Pitfall 6 (qty/lineCost rounded independently from the same
# raw qty_per_unit * quantity product).

def _serialize_bom_line(row):
    return {
        'code': row['code'],
        'name': row['name'],
        'unit': row['unit'],
        'unitCost': row['unit_cost'],
        'qtyPerUnit': row['qty_per_unit'],
    }


@production_bp.route('/api/bom/<product_code>', methods=['GET'])
@login_required
def get_bom(product_code):
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT code, name, unit, unit_cost, qty_per_unit FROM bom_lines '
            'WHERE product_code = ? ORDER BY id',
            (product_code,),
        ).fetchall()
        return jsonify({'success': True, 'lines': [_serialize_bom_line(r) for r in rows]})
    finally:
        conn.close()


@production_bp.route('/api/bom/<product_code>', methods=['PUT'])
@login_required
def save_bom(product_code):
    data = request.get_json(silent=True) or {}
    lines = data.get('lines') or []

    clean = []
    for l in lines:
        try:
            qty_per_unit = float(l.get('qtyPerUnit') or 0)
        except (TypeError, ValueError):
            qty_per_unit = 0
        if not l.get('code') or not l.get('name') or qty_per_unit <= 0:
            continue
        unit = (l.get('unit') or 'cái').strip() or 'cái'
        try:
            unit_cost = float(l.get('unitCost') or 0)
        except (TypeError, ValueError):
            unit_cost = 0
        clean.append({
            'code': l['code'],
            'name': l['name'],
            'unit': unit,
            'unit_cost': unit_cost,
            'qty_per_unit': qty_per_unit,
        })

    if not clean:
        return jsonify({
            'success': False,
            'message': 'Cần ít nhất 1 dòng nguyên vật liệu hợp lệ (mã, tên, định mức > 0)',
        }), 400

    conn = get_connection()
    try:
        conn.execute('DELETE FROM bom_lines WHERE product_code = ?', (product_code,))
        for l in clean:
            conn.execute(
                'INSERT INTO bom_lines (product_code, code, name, unit, unit_cost, qty_per_unit) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (product_code, l['code'], l['name'], l['unit'], l['unit_cost'], l['qty_per_unit']),
            )
        conn.commit()
        return jsonify({
            'success': True,
            'message': 'Lưu định mức thành công',
            'lines': [
                {
                    'code': l['code'], 'name': l['name'], 'unit': l['unit'],
                    'unitCost': l['unit_cost'], 'qtyPerUnit': l['qty_per_unit'],
                }
                for l in clean
            ],
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@production_bp.route('/api/bom/calculate', methods=['POST'])
@login_required
def calculate_bom():
    data = request.get_json(silent=True) or {}
    product_code = data.get('productCode')
    try:
        qty = float(data.get('quantity') or 0)
    except (TypeError, ValueError):
        qty = 0

    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT code, name, unit, unit_cost, qty_per_unit FROM bom_lines WHERE product_code = ?',
            (product_code,),
        ).fetchall()
        lines = []
        total_cost = 0
        for r in rows:
            line_qty = round(r['qty_per_unit'] * qty, 2)
            line_cost = round(r['qty_per_unit'] * qty * r['unit_cost'])
            total_cost += line_cost
            lines.append({
                'code': r['code'],
                'name': r['name'],
                'unit': r['unit'],
                'unitCost': r['unit_cost'],
                'qtyPerUnit': r['qty_per_unit'],
                'qty': line_qty,
                'lineCost': line_cost,
            })
        return jsonify({
            'success': True,
            'lines': lines,
            'totalCost': total_cost,
            'quantity': qty,
        })
    finally:
        conn.close()
