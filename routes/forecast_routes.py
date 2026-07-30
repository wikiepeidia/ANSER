"""Material-demand forecast route (N8N-03).

Trailing-average method only: velocity = recent production_orders quantity
(over windowDays) / windowDays, projected over horizonDays, multiplied by
each product's bom_lines.qty_per_unit. This is deliberately NOT a machine-
learning forecast -- see the locked "simple historical basis" decision in
.planning/phases/05-ai-services-automation-completion/05-CONTEXT.md.

Implemented entirely inside anser-san-xuat: _compute_material_forecast reads
only production_orders and bom_lines via core.sanxuat_db.get_connection(),
never an HTTP call into another branch/app (ROADMAP.md's Branch Scope).
"""
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import login_required

from core.sanxuat_db import get_connection

forecast_bp = Blueprint('forecast', __name__)


def _parse_ts(value):
    """Normalize a production_orders.created_at value to a datetime.

    SQLite returns the plain '%Y-%m-%d %H:%M:%S' string always written by
    core.sanxuat_db.now(); the Postgres driver (psycopg2) returns a native
    datetime object for the same TIMESTAMP column on read. Window filtering
    needs a real comparable datetime either way.
    """
    if isinstance(value, str):
        return datetime.strptime(value[:19], '%Y-%m-%d %H:%M:%S')
    return value


def _compute_material_forecast(conn, window_days, horizon_days, product_code=None):
    """Trailing-average material-demand forecast.

    Returns (products, materials): products is a per-product breakdown with
    velocity/projected quantity and per-BOM-line forecast; materials is the
    same data aggregated across products by materialCode.
    """
    query = 'SELECT * FROM production_orders WHERE is_deleted = FALSE'
    params = ()
    if product_code:
        query += ' AND product_code = ?'
        params = (product_code,)
    rows = conn.execute(query, params).fetchall()

    cutoff = datetime.now() - timedelta(days=window_days)
    qty_by_product = {}
    count_by_product = {}
    for row in rows:
        ts = _parse_ts(row['created_at'])
        if ts is None or ts < cutoff:
            continue
        code = row['product_code']
        qty_by_product[code] = qty_by_product.get(code, 0) + row['quantity']
        count_by_product[code] = count_by_product.get(code, 0) + 1

    materials_agg = {}
    products = []
    for code, total_qty in qty_by_product.items():
        velocity_per_day = round(total_qty / window_days, 4)
        projected_qty = round(velocity_per_day * horizon_days, 2)

        bom_rows = conn.execute(
            'SELECT code, name, unit, unit_cost, qty_per_unit FROM bom_lines WHERE product_code = ?',
            (code,),
        ).fetchall()

        lines = []
        for bom in bom_rows:
            forecast_qty = round(bom['qty_per_unit'] * projected_qty, 2)
            forecast_cost = round(forecast_qty * bom['unit_cost'])
            lines.append({
                'materialCode': bom['code'],
                'materialName': bom['name'],
                'unit': bom['unit'],
                'unitCost': bom['unit_cost'],
                'forecastQty': forecast_qty,
                'forecastCost': forecast_cost,
            })
            entry = materials_agg.setdefault(bom['code'], {
                'materialCode': bom['code'],
                'materialName': bom['name'],
                'unit': bom['unit'],
                'totalForecastQty': 0,
                'totalForecastCost': 0,
            })
            entry['totalForecastQty'] = round(entry['totalForecastQty'] + forecast_qty, 2)
            entry['totalForecastCost'] += forecast_cost

        products.append({
            'productCode': code,
            'ordersInWindow': count_by_product[code],
            'quantityInWindow': round(total_qty, 2),
            'velocityPerDay': velocity_per_day,
            'projectedQty': projected_qty,
            'lines': lines,
        })

    materials = sorted(materials_agg.values(), key=lambda e: e['materialCode'])
    return products, materials


@forecast_bp.route('/api/forecast/materials', methods=['GET'])
@login_required
def get_material_forecast():
    try:
        window_days = int(request.args.get('windowDays', 30))
    except (TypeError, ValueError):
        window_days = -1
    default_horizon = window_days if window_days > 0 else 30
    try:
        horizon_days = int(request.args.get('horizonDays', default_horizon))
    except (TypeError, ValueError):
        horizon_days = -1

    if window_days <= 0 or horizon_days <= 0:
        return jsonify({
            'success': False,
            'message': 'windowDays và horizonDays phải là số nguyên dương',
        }), 400

    product_code = request.args.get('productCode')

    conn = get_connection()
    try:
        products, materials = _compute_material_forecast(
            conn, window_days, horizon_days, product_code
        )
        return jsonify({
            'success': True,
            'method': 'trailing_average',
            'windowDays': window_days,
            'horizonDays': horizon_days,
            'productCode': product_code,
            'note': (
                'Dự báo theo phương pháp trung bình trượt (trailing average): '
                'vận tốc sản xuất = tổng số lượng các đơn sản xuất trong '
                'windowDays ngày gần nhất / windowDays, chiếu sang horizonDays '
                'ngày tới, rồi nhân với định mức BOM (qty_per_unit) để ra nhu '
                'cầu nguyên vật liệu dự kiến. Đây KHÔNG phải mô hình học máy, '
                'chỉ là phép ngoại suy tuyến tính từ lịch sử đơn hàng gần nhất.'
            ),
            'products': products,
            'materials': materials,
        })
    finally:
        conn.close()
