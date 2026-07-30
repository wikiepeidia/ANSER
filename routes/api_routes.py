"""API routes for San Xuat's own business data — fully separate from ANSER."""
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.auth import require_role
from core.sanxuat_db import get_connection, now

api_bp = Blueprint('api', __name__)


# ── Products ─────────────────────────────────────────────────────────────

@api_bp.route('/api/products', methods=['GET'])
@login_required
def get_products():
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT id, code, name, category, unit, price, stock_quantity, '
            'description, image_url, created_at, updated_at FROM products '
            'ORDER BY created_at DESC'
        ).fetchall()
        return jsonify({'success': True, 'products': [dict(r) for r in rows]})
    finally:
        conn.close()


@api_bp.route('/api/products', methods=['POST'])
@login_required
def create_product():
    data = request.get_json(silent=True) or {}
    if not data.get('code') or not data.get('name'):
        return jsonify({'success': False, 'message': 'Thiếu mã hoặc tên sản phẩm'}), 400
    conn = get_connection()
    try:
        conn.execute(
            'INSERT INTO products (code, name, category, unit, price, stock_quantity, '
            'description, image_url, created_by, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (data['code'], data['name'], data.get('category', ''), data.get('unit', 'cái'),
             data.get('price', 0), data.get('stock_quantity', 0), data.get('description', ''),
             data.get('image_url', ''), current_user.id, now(), now()),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Tạo sản phẩm thành công'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Mã sản phẩm đã tồn tại hoặc lỗi: {e}'}), 400
    finally:
        conn.close()


@api_bp.route('/api/products/<int:product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    data = request.get_json(silent=True) or {}
    conn = get_connection()
    try:
        cur = conn.execute('SELECT id FROM products WHERE id = ?', (product_id,))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'Không tìm thấy sản phẩm'}), 404
        conn.execute(
            'UPDATE products SET name=?, category=?, unit=?, price=?, stock_quantity=?, '
            'description=?, image_url=?, updated_at=? WHERE id=?',
            (data.get('name'), data.get('category', ''), data.get('unit', 'cái'),
             data.get('price', 0), data.get('stock_quantity', 0), data.get('description', ''),
             data.get('image_url', ''), now(), product_id),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Cập nhật sản phẩm thành công'})
    finally:
        conn.close()


@api_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
@require_role('manager')
def delete_product(product_id):
    conn = get_connection()
    try:
        conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Xóa sản phẩm thành công'})
    finally:
        conn.close()


# ── Customers ────────────────────────────────────────────────────────────

@api_bp.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT id, code, name, phone, email, address, notes, created_at '
            'FROM customers ORDER BY created_at DESC'
        ).fetchall()
        return jsonify({'success': True, 'customers': [dict(r) for r in rows]})
    finally:
        conn.close()


@api_bp.route('/api/customers', methods=['POST'])
@login_required
def create_customer():
    data = request.get_json(silent=True) or {}
    if not data.get('name'):
        return jsonify({'success': False, 'message': 'Thiếu tên khách hàng'}), 400
    conn = get_connection()
    try:
        code = data.get('code') or f"KH-{datetime.now().strftime('%H%M%S')}-{secrets.token_hex(2).upper()}"
        cur = conn.execute(
            'INSERT INTO customers (code, name, phone, email, address, notes, created_by, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (code, data['name'], data.get('phone', ''), data.get('email', ''),
             data.get('address', ''), data.get('notes', ''), current_user.id, now()),
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Tạo khách hàng thành công', 'id': cur.lastrowid, 'code': code})
    finally:
        conn.close()


# ── Imports ──────────────────────────────────────────────────────────────

def _resolve_product(conn, item, user_id):
    product_id = item.get('product_id')
    code = (item.get('product_code') or '').strip()
    name = (item.get('product_name') or '').strip()
    if product_id:
        return product_id
    if code:
        row = conn.execute('SELECT id FROM products WHERE code = ?', (code,)).fetchone()
        if row:
            return row['id']
    if name:
        row = conn.execute('SELECT id FROM products WHERE name = ?', (name,)).fetchone()
        if row:
            return row['id']
    # Auto-create a new product from this line item
    unit_price = float(item.get('unit_price', 0))
    new_code = code or f"P-{datetime.now().strftime('%H%M%S')}-{secrets.token_hex(2).upper()}"
    new_name = name or new_code
    cur = conn.execute(
        'INSERT INTO products (code, name, price, stock_quantity, created_by, created_at, updated_at) '
        'VALUES (?, ?, ?, 0, ?, ?, ?)',
        (new_code, new_name, unit_price, user_id, now(), now()),
    )
    return cur.lastrowid


@api_bp.route('/api/imports', methods=['GET'])
@login_required
def get_imports():
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT id, code, supplier_name, total_amount, notes, status, created_at '
            'FROM import_transactions ORDER BY created_at DESC'
        ).fetchall()
        return jsonify({'success': True, 'imports': [dict(r) for r in rows]})
    finally:
        conn.close()


@api_bp.route('/api/imports', methods=['POST'])
@login_required
def create_import():
    data = request.get_json(silent=True) or {}
    items = data.get('items') or []
    if not items:
        return jsonify({'success': False, 'message': 'Không có sản phẩm nào trong phiếu nhập'}), 400

    conn = get_connection()
    try:
        code = f"PN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        total = sum(float(it.get('quantity', 0)) * float(it.get('unit_price', 0)) for it in items)
        cur = conn.execute(
            'INSERT INTO import_transactions (code, supplier_name, total_amount, notes, created_by, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (code, data.get('supplier_name', ''), total, data.get('notes', ''), current_user.id, now()),
        )
        import_id = cur.lastrowid

        for it in items:
            qty = float(it.get('quantity', 0))
            price = float(it.get('unit_price', 0))
            product_id = _resolve_product(conn, it, current_user.id)
            conn.execute(
                'INSERT INTO import_details (import_id, product_id, quantity, unit_price, total_price) '
                'VALUES (?, ?, ?, ?, ?)',
                (import_id, product_id, qty, price, qty * price),
            )
            conn.execute(
                'UPDATE products SET stock_quantity = stock_quantity + ?, updated_at = ? WHERE id = ?',
                (qty, now(), product_id),
            )

        conn.commit()
        return jsonify({'success': True, 'message': 'Tạo phiếu nhập thành công', 'id': import_id, 'code': code})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


# ── Exports ──────────────────────────────────────────────────────────────

@api_bp.route('/api/exports', methods=['GET'])
@login_required
def get_exports():
    conn = get_connection()
    try:
        rows = conn.execute(
            'SELECT e.id, e.code, e.customer_id, e.total_amount, e.notes, e.status, e.created_at, '
            'c.name AS customer_name FROM export_transactions e '
            'LEFT JOIN customers c ON e.customer_id = c.id ORDER BY e.created_at DESC'
        ).fetchall()
        return jsonify({'success': True, 'exports': [dict(r) for r in rows]})
    finally:
        conn.close()


@api_bp.route('/api/exports', methods=['POST'])
@login_required
def create_export():
    data = request.get_json(silent=True) or {}
    items = data.get('items') or []
    customer_id = data.get('customer_id')
    if not items:
        return jsonify({'success': False, 'message': 'Không có sản phẩm nào trong phiếu xuất'}), 400

    conn = get_connection()
    try:
        # Resolve products + check stock before writing anything
        resolved = []
        for it in items:
            product_id = _resolve_product(conn, it, current_user.id)
            qty = float(it.get('quantity', 0))
            price = float(it.get('unit_price', 0))
            row = conn.execute('SELECT stock_quantity, name FROM products WHERE id = ?', (product_id,)).fetchone()
            if not row or row['stock_quantity'] < qty:
                conn.rollback()
                available = row['stock_quantity'] if row else 0
                name = row['name'] if row else product_id
                return jsonify({'success': False, 'message': f'Không đủ tồn kho cho "{name}" (còn {available})'}), 409
            resolved.append((product_id, qty, price))

        code = f"PX-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        total = sum(qty * price for _, qty, price in resolved)
        cur = conn.execute(
            'INSERT INTO export_transactions (code, customer_id, total_amount, notes, created_by, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (code, customer_id, total, data.get('notes', ''), current_user.id, now()),
        )
        export_id = cur.lastrowid

        for product_id, qty, price in resolved:
            conn.execute(
                'INSERT INTO export_details (export_id, product_id, quantity, unit_price, total_price) '
                'VALUES (?, ?, ?, ?, ?)',
                (export_id, product_id, qty, price, qty * price),
            )
            conn.execute(
                'UPDATE products SET stock_quantity = stock_quantity - ?, updated_at = ? WHERE id = ?',
                (qty, now(), product_id),
            )

        conn.commit()
        return jsonify({'success': True, 'message': 'Tạo phiếu xuất thành công', 'id': export_id, 'code': code})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()


# ── Dashboard stats ──────────────────────────────────────────────────────

@api_bp.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    conn = get_connection()
    try:
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0).strftime('%Y-%m-%d %H:%M:%S')
        revenue = conn.execute(
            'SELECT COALESCE(SUM(total_amount), 0) AS v FROM export_transactions WHERE created_at >= ?',
            (start_of_month,),
        ).fetchone()['v']
        today_start = datetime.now().strftime('%Y-%m-%d 00:00:00')
        tomorrow_start = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d 00:00:00')
        new_orders = conn.execute(
            'SELECT COUNT(*) AS c FROM export_transactions WHERE created_at >= ? AND created_at < ?',
            (today_start, tomorrow_start),
        ).fetchone()['c']
        return jsonify({'success': True, 'revenue': revenue, 'new_orders': new_orders, 'active_projects': 0})
    finally:
        conn.close()
