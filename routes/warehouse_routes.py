"""Warehouse, storage-location, and stock-ledger routes — real backend for
TRACE-03/04/05.

Replaces the localStorage mock in static/js/store.js (WAREHOUSES /
warehouseLocations / warehouseStock arrays, transferStock / recordStockCount
functions). Current stock is always derived via SUM(quantity_delta) over the
append-only stock_ledger table (02-01) — there is no separately mutated
"current stock" column anywhere in this file. A transfer is exactly 2 linked
ledger rows sharing one transfer_group, written atomically; a stocktake is
exactly 1 adjustment row. See .planning/phases/02-material-batches-
warehouses-traceability-suppliers/02-RESEARCH.md (Patterns 2-4) for the
locked design this file implements.

This file deliberately never reads or writes products.stock_quantity
(Phase 1's flat, warehouse-less field) — the warehouse ledger is a fully
separate, deliberately unreconciled stock concept this phase (Pitfall 4).
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.sanxuat_db import get_connection, now

warehouse_bp = Blueprint('warehouse', __name__)


def _serialize_warehouse(row):
    return {
        'id': row['id'],
        'code': row['code'],
        'name': row['name'],
        'address': row['address'] or '',
    }


def _serialize_location(row):
    return {
        'id': row['id'],
        'warehouseId': row['warehouse_id'],
        'code': row['code'],
        'name': row['name'],
    }


def _current_stock(conn, warehouse_id, location_id, product_code):
    """Fresh current-stock balance for one (warehouse, location, product)
    triple, computed via SUM(quantity_delta) over stock_ledger. Must be
    queried immediately before any insufficient-stock decision (never
    reused from a prior response) — Pitfall 5."""
    row = conn.execute(
        'SELECT COALESCE(SUM(quantity_delta), 0) AS qty FROM stock_ledger '
        'WHERE warehouse_id = ? AND location_id = ? AND product_code = ?',
        (warehouse_id, location_id, product_code),
    ).fetchone()
    return float(row['qty'])


# ── Warehouse CRUD (TRACE-03) ────────────────────────────────────────────

@warehouse_bp.route('/api/warehouses', methods=['GET'])
@login_required
def get_warehouses():
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM warehouses WHERE is_deleted = FALSE ORDER BY code'
        ).fetchall()
        return jsonify({'success': True, 'warehouses': [_serialize_warehouse(r) for r in rows]})
    finally:
        conn.close()


@warehouse_bp.route('/api/warehouses', methods=['POST'])
@login_required
def create_warehouse():
    data = request.get_json(silent=True) or {}
    code = data.get('code')
    name = data.get('name')
    if not code or not name:
        return jsonify({'success': False, 'message': 'Thiếu mã hoặc tên kho'}), 400

    conn = get_connection()
    try:
        cur = conn.execute(
            'INSERT INTO warehouses (code, name, address, created_by, created_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (code, name, data.get('address', ''), current_user.id, now()),
        )
        conn.commit()
        return jsonify({'success': True, 'id': cur.lastrowid, 'code': code})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@warehouse_bp.route('/api/warehouses/<int:warehouse_id>', methods=['PUT'])
@login_required
def update_warehouse(warehouse_id):
    data = request.get_json(silent=True) or {}
    code = data.get('code')
    name = data.get('name')
    if not code or not name:
        return jsonify({'success': False, 'message': 'Thiếu mã hoặc tên kho'}), 400

    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM warehouses WHERE id = ? AND is_deleted = FALSE', (warehouse_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy kho'}), 404
        conn.execute(
            'UPDATE warehouses SET code=?, name=?, address=? WHERE id=?',
            (code, name, data.get('address', ''), warehouse_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Cập nhật kho thành công'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@warehouse_bp.route('/api/warehouses/<int:warehouse_id>', methods=['DELETE'])
@login_required
def delete_warehouse(warehouse_id):
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM warehouses WHERE id = ? AND is_deleted = FALSE', (warehouse_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy kho'}), 404
        # Soft-deletes the warehouse row only — does NOT cascade to its
        # locations, each location's own lifecycle is independent (A4).
        conn.execute(
            'UPDATE warehouses SET is_deleted = TRUE, deleted_at = ? WHERE id = ?',
            (now(), warehouse_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Xóa kho thành công'})
    finally:
        conn.close()


# ── Storage location CRUD (TRACE-03) ─────────────────────────────────────

@warehouse_bp.route('/api/warehouses/<int:warehouse_id>/locations', methods=['GET'])
@login_required
def get_warehouse_locations(warehouse_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT * FROM warehouse_locations WHERE warehouse_id = ? AND is_deleted = FALSE '
            'ORDER BY code',
            (warehouse_id,),
        ).fetchall()
        return jsonify({'success': True, 'locations': [_serialize_location(r) for r in rows]})
    finally:
        conn.close()


@warehouse_bp.route('/api/warehouse-locations', methods=['POST'])
@login_required
def create_warehouse_location():
    data = request.get_json(silent=True) or {}
    warehouse_id = data.get('warehouseId')
    code = data.get('code')
    name = data.get('name')
    if not warehouse_id or not code or not name:
        return jsonify({'success': False, 'message': 'Thiếu kho, mã hoặc tên vị trí'}), 400

    conn = get_connection()
    try:
        wh = conn.execute(
            'SELECT id FROM warehouses WHERE id = ? AND is_deleted = FALSE', (warehouse_id,)
        ).fetchone()
        if not wh:
            return jsonify({'success': False, 'message': 'Không tìm thấy kho'}), 404
        cur = conn.execute(
            'INSERT INTO warehouse_locations (warehouse_id, code, name) VALUES (?, ?, ?)',
            (warehouse_id, code, name),
        )
        conn.commit()
        return jsonify({'success': True, 'id': cur.lastrowid, 'warehouseId': warehouse_id, 'code': code})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@warehouse_bp.route('/api/warehouse-locations/<int:location_id>', methods=['PUT'])
@login_required
def update_warehouse_location(location_id):
    data = request.get_json(silent=True) or {}
    code = data.get('code')
    name = data.get('name')
    if not code or not name:
        return jsonify({'success': False, 'message': 'Thiếu kho, mã hoặc tên vị trí'}), 400

    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM warehouse_locations WHERE id = ? AND is_deleted = FALSE',
            (location_id,),
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy vị trí kho'}), 404
        conn.execute(
            'UPDATE warehouse_locations SET code=?, name=? WHERE id=?',
            (code, name, location_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Cập nhật vị trí kho thành công'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@warehouse_bp.route('/api/warehouse-locations/<int:location_id>', methods=['DELETE'])
@login_required
def delete_warehouse_location(location_id):
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT id FROM warehouse_locations WHERE id = ? AND is_deleted = FALSE',
            (location_id,),
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy vị trí kho'}), 404
        # No check against stock_ledger balance — allowed regardless of
        # whether a nonzero balance still references this location_id (A4).
        conn.execute(
            'UPDATE warehouse_locations SET is_deleted = TRUE, deleted_at = ? WHERE id = ?',
            (now(), location_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Xóa vị trí kho thành công'})
    finally:
        conn.close()


# ── Current-stock projection (TRACE-03) ──────────────────────────────────

@warehouse_bp.route('/api/warehouse-stock', methods=['GET'])
@login_required
def get_warehouse_stock():
    warehouse_id = request.args.get('warehouseId', type=int)
    conn = get_connection()
    try:
        query = (
            'SELECT warehouse_id, location_id, product_code, product_name, unit, '
            'SUM(quantity_delta) AS quantity FROM stock_ledger'
        )
        params = []
        if warehouse_id is not None:
            query += ' WHERE warehouse_id = ?'
            params.append(warehouse_id)
        query += (
            ' GROUP BY warehouse_id, location_id, product_code, product_name, unit '
            'HAVING SUM(quantity_delta) > 0'
        )
        rows = conn.execute(query, tuple(params)).fetchall()
        return jsonify({
            'success': True,
            'stock': [
                {
                    'warehouseId': r['warehouse_id'],
                    'locationId': r['location_id'],
                    'productCode': r['product_code'],
                    'productName': r['product_name'],
                    'unit': r['unit'],
                    'quantity': r['quantity'],
                }
                for r in rows
            ],
        })
    finally:
        conn.close()


def _resolve_product_display(conn, product_code):
    """Resolve product_name/unit for a ledger row from the products table
    (read-only lookup of code/name/unit only — never stock_quantity, per
    Pitfall 4). Falls back to the raw code / 'cái' if no match, matching
    the mock's lenient fallback."""
    row = conn.execute('SELECT name, unit FROM products WHERE code = ?', (product_code,)).fetchone()
    if row:
        return row['name'], row['unit'] or 'cái'
    return product_code, 'cái'


# ── Stock transfer + stocktake adjustment (TRACE-04, TRACE-05) ──────────

@warehouse_bp.route('/api/warehouse-stock/transfer', methods=['POST'])
@login_required
def transfer_stock():
    data = request.get_json(silent=True) or {}

    try:
        quantity = float(data.get('quantity'))
    except (TypeError, ValueError):
        quantity = 0
    if quantity <= 0:
        return jsonify({'success': False, 'message': 'Số lượng chuyển phải lớn hơn 0'}), 400

    product_code = data.get('productCode')
    from_warehouse_id = data.get('fromWarehouseId')
    from_location_id = data.get('fromLocationId')
    to_warehouse_id = data.get('toWarehouseId')
    to_location_id = data.get('toLocationId')

    if from_warehouse_id == to_warehouse_id and from_location_id == to_location_id:
        return jsonify({'success': False, 'message': 'Vị trí nguồn và đích phải khác nhau'}), 400

    conn = get_connection()
    try:
        # Fresh balance, queried immediately before the decision — never a
        # cached/previously-fetched figure (Pitfall 5).
        available = _current_stock(conn, from_warehouse_id, from_location_id, product_code)
        if available < quantity:
            return jsonify({
                'success': False,
                'message': f'Không đủ tồn kho tại vị trí nguồn (còn {available})',
            }), 409

        product_name, unit = _resolve_product_display(conn, product_code)
        note = data.get('note', '')

        cur = conn.execute(
            'INSERT INTO stock_ledger (entry_type, warehouse_id, location_id, product_code, '
            'product_name, unit, quantity_delta, counterparty_warehouse_id, '
            'counterparty_location_id, note, created_by, created_at) '
            "VALUES ('transfer_out', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (from_warehouse_id, from_location_id, product_code, product_name, unit, -quantity,
             to_warehouse_id, to_location_id, note, current_user.id, now()),
        )
        transfer_group = str(cur.lastrowid)
        conn.execute(
            'UPDATE stock_ledger SET transfer_group = ? WHERE id = ?',
            (transfer_group, cur.lastrowid),
        )
        conn.execute(
            'INSERT INTO stock_ledger (entry_type, warehouse_id, location_id, product_code, '
            'product_name, unit, quantity_delta, transfer_group, counterparty_warehouse_id, '
            'counterparty_location_id, note, created_by, created_at) '
            "VALUES ('transfer_in', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (to_warehouse_id, to_location_id, product_code, product_name, unit, quantity,
             transfer_group, from_warehouse_id, from_location_id, note, current_user.id, now()),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Chuyển kho thành công'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@warehouse_bp.route('/api/warehouse-stock/stocktake', methods=['POST'])
@login_required
def stocktake_adjustment():
    data = request.get_json(silent=True) or {}

    try:
        counted_qty = float(data.get('countedQty'))
    except (TypeError, ValueError):
        counted_qty = None
    if counted_qty is None or counted_qty < 0:
        return jsonify({'success': False, 'message': 'Số lượng đếm không hợp lệ'}), 400

    warehouse_id = data.get('warehouseId')
    location_id = data.get('locationId')
    product_code = data.get('productCode')

    conn = get_connection()
    try:
        system_qty = _current_stock(conn, warehouse_id, location_id, product_code)
        product_name, unit = _resolve_product_display(conn, product_code)
        quantity_delta = counted_qty - system_qty

        conn.execute(
            'INSERT INTO stock_ledger (entry_type, warehouse_id, location_id, product_code, '
            'product_name, unit, quantity_delta, system_qty_snapshot, counted_qty, note, '
            'created_by, created_at) '
            "VALUES ('adjustment', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (warehouse_id, location_id, product_code, product_name, unit, quantity_delta,
             system_qty, counted_qty, data.get('note', ''), current_user.id, now()),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Ghi nhận kiểm kê thành công'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


@warehouse_bp.route('/api/warehouse-stock/ledger', methods=['GET'])
@login_required
def get_stock_ledger():
    warehouse_id = request.args.get('warehouseId', type=int)
    location_id = request.args.get('locationId', type=int)
    product_code = request.args.get('productCode')
    entry_type = request.args.get('entryType')

    conditions = []
    params = []
    if warehouse_id is not None:
        conditions.append('warehouse_id = ?')
        params.append(warehouse_id)
    if location_id is not None:
        conditions.append('location_id = ?')
        params.append(location_id)
    if product_code:
        conditions.append('product_code = ?')
        params.append(product_code)
    if entry_type:
        conditions.append('entry_type = ?')
        params.append(entry_type)

    query = 'SELECT * FROM stock_ledger'
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    query += ' ORDER BY created_at DESC'

    conn = get_connection()
    try:
        rows = conn.execute(query, tuple(params)).fetchall()
        entries = [
            {
                'id': r['id'],
                'entryType': r['entry_type'],
                'warehouseId': r['warehouse_id'],
                'locationId': r['location_id'],
                'productCode': r['product_code'],
                'productName': r['product_name'],
                'unit': r['unit'],
                'quantityDelta': r['quantity_delta'],
                'transferGroup': r['transfer_group'],
                'counterpartyWarehouseId': r['counterparty_warehouse_id'],
                'counterpartyLocationId': r['counterparty_location_id'],
                'systemQtySnapshot': r['system_qty_snapshot'],
                'countedQty': r['counted_qty'],
                'note': r['note'],
                'createdAt': r['created_at'],
            }
            for r in rows
        ]
        return jsonify({'success': True, 'entries': entries})
    finally:
        conn.close()
