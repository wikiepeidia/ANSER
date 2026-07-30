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
from flask import Blueprint, jsonify
from flask_login import login_required

from core.sanxuat_db import get_connection

costing_bp = Blueprint('costing', __name__)


def _compute_order_costing(conn, order_row):
    """Shared cost/waste/profit computation for a single production order.

    Called by both GET .../costing (this file) and GET /api/costing/reports
    (added in Task 2 -- batch and shift grouping) so the material_cost/
    waste_cost formula is computed identically everywhere, never
    duplicated/diverging.
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
