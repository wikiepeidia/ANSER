"""Admin subscription-management routes — admin_sub_bp Blueprint."""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.services.subscription_service import (
    check_expired_subscriptions, extend_subscription, get_all_subscriptions,
    get_subscription_history, set_auto_renew,
)

admin_sub_bp = Blueprint('admin_subs', __name__)


@admin_sub_bp.route('/api/admin/subscriptions', methods=['GET'])
@login_required
def api_get_subscriptions():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    return jsonify({'success': True, 'subscriptions': get_all_subscriptions()})


@admin_sub_bp.route('/api/admin/subscription/auto-renew', methods=['POST'])
@login_required
def api_toggle_auto_renew():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    data = request.get_json()
    user_id = data.get('user_id')
    auto_renew = data.get('auto_renew', False)
    if not user_id:
        return jsonify({'success': False, 'message': 'Thiếu user_id'}), 400
    try:
        set_auto_renew(user_id, auto_renew)
        return jsonify({'success': True, 'message': 'Đã cập nhật tự động gia hạn'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_sub_bp.route('/api/admin/subscription/extend', methods=['POST'])
@login_required
def api_extend_subscription():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    data = request.get_json()
    user_id = data.get('user_id')
    plan_type = data.get('plan_type')
    payment_method = data.get('payment_method', 'manual')
    transaction_id = data.get('transaction_id')
    if not user_id or not plan_type:
        return jsonify({'success': False, 'message': 'Thiếu các trường bắt buộc'}), 400
    try:
        new_expiry = extend_subscription(user_id, plan_type, payment_method, transaction_id)
        return jsonify({'success': True,
                        'message': f'Gia hạn thành công đến {new_expiry}',
                        'new_expiry': new_expiry})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_sub_bp.route('/api/admin/subscription-history', methods=['GET'])
@login_required
def api_get_subscription_history():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    return jsonify({'success': True, 'history': get_subscription_history()})


@admin_sub_bp.route('/api/admin/extend-subscription', methods=['POST'])
@login_required
def api_extend_subscription_v2():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    data = request.get_json()
    user_id = data.get('user_id')
    subscription_type = data.get('subscription_type')
    payment_method = data.get('payment_method')
    transaction_id = data.get('transaction_id', '')
    if subscription_type not in ('monthly', 'quarterly', 'yearly'):
        return jsonify({'success': False, 'message': 'Loại đăng ký không hợp lệ'}), 400
    try:
        new_expiry = extend_subscription(user_id, subscription_type, payment_method, transaction_id)
        return jsonify({'success': True, 'message': 'Gia hạn đăng ký thành công'})
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_sub_bp.route('/api/admin/check-expired-subscriptions', methods=['POST'])
@login_required
def api_check_expired_subscriptions():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    try:
        count = check_expired_subscriptions()
        return jsonify({'success': True, 'demoted_count': count,
                        'message': f'Đã hạ cấp {count} manager hết hạn'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
