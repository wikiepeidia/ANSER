"""Core product/customer API and logout — main_bp Blueprint."""
from flask import Blueprint, flash, jsonify, redirect, request, url_for
from flask_login import current_user, login_required, logout_user

from core.services.customer_service import (
    create_customer, delete_customer, get_all_customers, update_customer,
)
from core.services.product_service import (
    create_product, delete_product, get_all_products, import_products_from_excel,
    update_product,
)

main_bp = Blueprint('main', __name__)


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất thành công.', 'success')
    return redirect(url_for('auth.signin'))


# ── Customers ──────────────────────────────────────────────────────────────

@main_bp.route('/api/customers', methods=['GET'])
@login_required
def api_get_customers():
    return jsonify({'success': True, 'customers': get_all_customers()})


@main_bp.route('/api/customers', methods=['POST'])
@login_required
def api_create_customer():
    data = request.get_json()
    if not data or 'code' not in data or 'name' not in data:
        return jsonify({'success': False, 'message': 'Thiếu các trường bắt buộc'}), 400
    ok, err = create_customer(
        data['code'], data['name'], data.get('phone', ''), data.get('email', ''),
        data.get('address', ''), data.get('notes', ''), current_user.id,
    )
    if ok:
        return jsonify({'success': True, 'message': 'Tạo khách hàng thành công'})
    return jsonify({'success': False, 'message': err}), 400


@main_bp.route('/api/customers/<int:customer_id>', methods=['PUT'])
@login_required
def api_update_customer(customer_id):
    data = request.get_json()
    update_customer(
        customer_id, data['name'], data.get('phone', ''), data.get('email', ''),
        data.get('address', ''), data.get('notes', ''),
    )
    return jsonify({'success': True, 'message': 'Cập nhật khách hàng thành công'})


@main_bp.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@login_required
def api_delete_customer(customer_id):
    delete_customer(customer_id)
    return jsonify({'success': True, 'message': 'Xóa khách hàng thành công'})


# ── Products ───────────────────────────────────────────────────────────────

@main_bp.route('/api/products', methods=['GET'])
@login_required
def api_get_products():
    return jsonify({'success': True, 'products': get_all_products()})


@main_bp.route('/api/products', methods=['POST'])
@login_required
def api_create_product():
    data = request.get_json()
    if not data or 'code' not in data or 'name' not in data:
        return jsonify({'success': False, 'message': 'Thiếu các trường bắt buộc'}), 400
    ok, err = create_product(
        data['code'], data['name'], data.get('category', ''), data.get('unit', 'cái'),
        data.get('price', 0), data.get('stock_quantity', 0), data.get('description', ''),
        current_user.id,
    )
    if ok:
        return jsonify({'success': True, 'message': 'Tạo sản phẩm thành công'})
    return jsonify({'success': False, 'message': err}), 400


@main_bp.route('/api/products/<int:product_id>', methods=['PUT'])
@login_required
def api_update_product(product_id):
    data = request.get_json()
    update_product(
        product_id, data['name'], data.get('category', ''), data.get('unit', 'cái'),
        data.get('price', 0), data.get('stock_quantity', 0), data.get('description', ''),
    )
    return jsonify({'success': True, 'message': 'Cập nhật sản phẩm thành công'})


@main_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
def api_delete_product(product_id):
    delete_product(product_id)
    return jsonify({'success': True, 'message': 'Xóa sản phẩm thành công'})


@main_bp.route('/api/products/import-excel', methods=['POST'])
@login_required
def api_import_products_excel():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Không có file được gửi lên'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': 'Chưa chọn file'}), 400
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        return jsonify({'success': False, 'message': 'Chỉ chấp nhận file .xlsx hoặc .xls'}), 400
    try:
        result = import_products_from_excel(file, current_user.id)
        total = result['inserted'] + result['updated']
        return jsonify({
            'success': True,
            'message': f"Import thành công: {result['inserted']} thêm mới, {result['updated']} cập nhật, {result['skipped']} bỏ qua",
            **result,
        })
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi server: {e}'}), 500
