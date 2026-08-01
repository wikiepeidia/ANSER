"""Production-order costing routes (COST-01, COST-02).

Standard-cost valued: material_cost = bom_lines.unit_cost * qty_per_unit *
order quantity (planned/BOM basis). waste_cost = (actual batch_usage.
quantity_used - planned qty) * unit_cost, only when actual exceeds planned
(never negative). total_cost = material_cost + waste_cost. profit_estimate
= products.price * order quantity - total_cost.

Known, documented simplification: material_batches has no purchase-cost
column, so waste_cost is valued at BOM standard cost, not real money spent
on that specific batch — see .planning/phases/04-costing-invoice-data/
04-CONTEXT.md's Costing Model section for the locked rationale.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required

from core.sanxuat_db import get_connection

costing_bp = Blueprint('costing', __name__)


def _compute_order_costing(conn, order_row):
    """Shared cost/waste/profit computation for a single production order.

    Called by both GET .../costing (this file) and GET /api/costing/reports
    (batch and shift grouping) so the material_cost/waste_cost formula is
    computed identically everywhere, never duplicated/diverging.
    """
    bom_rows = conn.execute(
        'SELECT code, name, unit, unit_cost, qty_per_unit FROM bom_lines WHERE product_code = ?',
        (order_row['product_code'],),
    ).fetchall()

    lines = []
    material_cost = 0
    waste_cost = 0
    for r in bom_rows:
        planned_qty = round(r['qty_per_unit'] * order_row['quantity'], 2)
        material_cost_line = round(planned_qty * r['unit_cost'])
        material_cost += material_cost_line

        usage_rows = conn.execute(
            'SELECT mb.id AS batch_id, mb.batch_code, bu.quantity_used '
            'FROM batch_usage bu JOIN material_batches mb ON mb.id = bu.batch_id '
            'WHERE bu.order_id = ? AND mb.material_code = ?',
            (order_row['id'], r['code']),
        ).fetchall()
        actual_used = sum(u['quantity_used'] for u in usage_rows) if usage_rows else 0
        # Waste is never negative per material line — under-planned usage on
        # one BOM line must not create a negative adjustment that silently
        # offsets other lines' waste.
        waste_qty = max(0, round(actual_used - planned_qty, 2))
        waste_cost_line = round(waste_qty * r['unit_cost'])
        waste_cost += waste_cost_line

        lines.append({
            'materialCode': r['code'],
            'materialName': r['name'],
            'unit': r['unit'],
            'unitCost': r['unit_cost'],
            'plannedQty': planned_qty,
            'actualUsed': round(actual_used, 2),
            'wasteQty': waste_qty,
            'materialCostLine': material_cost_line,
            'wasteCostLine': waste_cost_line,
            'batchBreakdown': [
                {
                    'batchId': u['batch_id'],
                    'batchCode': u['batch_code'],
                    'quantityUsed': u['quantity_used'],
                }
                for u in usage_rows
            ],
        })

    total_cost = material_cost + waste_cost
    product = conn.execute(
        'SELECT price FROM products WHERE code = ?', (order_row['product_code'],)
    ).fetchone()
    price = product['price'] if product else 0
    profit_estimate = round(price * order_row['quantity'] - total_cost)

    return {
        'materialCost': material_cost,
        'wasteCost': waste_cost,
        'totalCost': total_cost,
        'profitEstimate': profit_estimate,
        'lines': lines,
    }


# ── Single order costing (COST-01) ───────────────────────────────────────

@costing_bp.route('/api/production-orders/<int:order_id>/costing', methods=['GET'])
@login_required
def get_order_costing(order_id):
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT * FROM production_orders WHERE id = ? AND is_deleted = FALSE', (order_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng'}), 404
        costing = _compute_order_costing(conn, row)
        return jsonify({
            'success': True,
            'orderId': row['id'],
            'orderCode': row['code'],
            'productCode': row['product_code'],
            'quantity': row['quantity'],
            **costing,
            'wasteCostNote': (
                'wasteCost được tính theo giá thành định mức BOM (unit_cost), '
                'KHÔNG phải giá nhập thực tế của lô NVL vì material_batches '
                'hiện chưa lưu giá mua.'
            ),
        })
    finally:
        conn.close()


# ── Cost/waste reports grouped by batch or shift (COST-02) ──────────────
# "shift" = calendar date of the order's completion ("Hoàn thành" event) or,
# absent that, its created_at date — a reporting-period grouping, not real
# shift scheduling (04-CONTEXT.md).

@costing_bp.route('/api/costing/reports', methods=['GET'])
@login_required
def get_costing_reports():
    group_by = request.args.get('groupBy', 'shift')
    if group_by not in ('batch', 'shift'):
        return jsonify({
            'success': False,
            'message': "Tham số groupBy không hợp lệ (chỉ nhận 'batch' hoặc 'shift')",
        }), 400

    conn = get_connection()
    try:
        orders = conn.execute(
            'SELECT * FROM production_orders WHERE is_deleted = FALSE'
        ).fetchall()

        if group_by == 'batch':
            batch_agg = {}
            for order in orders:
                costing = _compute_order_costing(conn, order)
                for line in costing['lines']:
                    actual_used = line['actualUsed']
                    for b in line['batchBreakdown']:
                        share = (b['quantityUsed'] / actual_used) if actual_used > 0 else 0
                        entry = batch_agg.setdefault(b['batchId'], {
                            'batchId': b['batchId'],
                            'batchCode': b['batchCode'],
                            'materialCode': line['materialCode'],
                            'materialName': line['materialName'],
                            'totalUsed': 0,
                            'materialCost': 0,
                            'wasteCost': 0,
                        })
                        entry['totalUsed'] = round(entry['totalUsed'] + b['quantityUsed'], 2)
                        entry['materialCost'] += round(b['quantityUsed'] * line['unitCost'])
                        entry['wasteCost'] += round(line['wasteCostLine'] * share)
            for entry in batch_agg.values():
                entry['totalCost'] = entry['materialCost'] + entry['wasteCost']
            report = sorted(batch_agg.values(), key=lambda e: e['batchId'])
        else:
            completion_rows = conn.execute(
                "SELECT order_id, MIN(created_at) AS completed_at FROM production_order_events "
                "WHERE event = 'Hoàn thành' GROUP BY order_id"
            ).fetchall()
            completion_map = {r['order_id']: r['completed_at'] for r in completion_rows}
            shift_agg = {}
            for order in orders:
                costing = _compute_order_costing(conn, order)
                shift_date = str(completion_map.get(order['id']) or order['created_at'])[:10]
                entry = shift_agg.setdefault(shift_date, {
                    'date': shift_date,
                    'orderCount': 0,
                    'materialCost': 0,
                    'wasteCost': 0,
                    'totalCost': 0,
                    'orderCodes': [],
                })
                entry['orderCount'] += 1
                entry['materialCost'] += costing['materialCost']
                entry['wasteCost'] += costing['wasteCost']
                entry['totalCost'] += costing['totalCost']
                entry['orderCodes'].append(order['code'])
            report = sorted(shift_agg.values(), key=lambda e: e['date'])

        return jsonify({'success': True, 'groupBy': group_by, 'report': report})
    finally:
        conn.close()
