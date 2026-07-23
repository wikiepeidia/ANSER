"""Admin and user-management routes — admin_user_bp Blueprint."""
from flask import Blueprint, jsonify, request
from flask_login import current_user

from core.extensions import db_manager
from core.security import require_role
from core.services.user_service import (
    admin_delete_user, delete_user, get_all_users,
    get_users_for_manager, reset_password, set_user_role,
)

admin_user_bp = Blueprint('admin_users', __name__)


@admin_user_bp.route('/api/admin/users')
@require_role('admin')
def admin_get_users():
    try:
        users = get_all_users()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_user_bp.route('/api/admin/activity')
@require_role('admin')
def admin_get_activity():
    activities = db_manager.get_recent_activities(limit=20)
    return jsonify({'success': True, 'activities': activities})


@admin_user_bp.route('/api/admin/stats')
@require_role('admin')
def admin_get_stats():
    return jsonify({'success': True, 'stats': {'users': 0, 'managers': 0, 'products': 0, 'customers': 0}})


@admin_user_bp.route('/api/admin/create-manager', methods=['POST'])
@require_role('admin')
def admin_create_manager():
    data = request.get_json()
    if not data or 'email' not in data or 'name' not in data or 'password' not in data:
        return jsonify({'success': False, 'message': 'Thiếu các trường bắt buộc'}), 400
    try:
        # Split name for the new create_user signature
        name_parts = data['name'].split()
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

        user_id = db_manager.create_user(
            data['email'], data['password'],
            first_name=first_name, last_name=last_name,
            role='manager'
        )
        return jsonify({'success': True, 'message': 'Tạo manager thành công', 'user_id': user_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@admin_user_bp.route('/api/create-user', methods=['POST'])
@require_role('manager')
def create_user():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'success': False, 'message': 'Thiếu các trường bắt buộc'}), 400
    try:
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        user_id = db_manager.create_user(
            data['email'], data['password'],
            first_name=first_name, last_name=last_name,
            role='employee', manager_id=current_user.id,
        )
        return jsonify({'success': True, 'message': 'Tạo tài khoản nhân viên thành công', 'user_id': user_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@admin_user_bp.route('/api/users', methods=['GET'])
@require_role('manager')
def get_users():
    role_filter = request.args.get('role')
    try:
        if current_user.role == 'manager':
            users = get_users_for_manager(current_user.id, role_filter)
        else:
            users = get_all_users(role_filter)
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_user_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@require_role('manager')
def delete_user_account(user_id):
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Không thể xóa tài khoản của chính mình'}), 400
    try:
        delete_user(user_id)
        return jsonify({'success': True, 'message': 'Xóa người dùng thành công'})
    except LookupError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except PermissionError as e:
        return jsonify({'success': False, 'message': str(e)}), 403
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_user_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@require_role('manager')
def reset_user_password(user_id):
    data = request.get_json()
    if not data or 'password' not in data:
        return jsonify({'success': False, 'message': 'Thiếu mật khẩu'}), 400
    new_password = data['password']
    if len(new_password) < 8:
        return jsonify({'success': False, 'message': 'Mật khẩu phải có ít nhất 8 ký tự'}), 400
    try:
        reset_password(user_id, new_password)
        return jsonify({'success': True, 'message': 'Đặt lại mật khẩu thành công'})
    except LookupError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_user_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@require_role('admin')
def admin_delete_user_route(user_id):
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Không thể xóa tài khoản của chính mình'}), 400
    try:
        admin_delete_user(user_id)
        return jsonify({'success': True, 'message': 'Xóa người dùng thành công'})
    except LookupError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_user_bp.route('/api/admin/users/promote', methods=['POST'])
@require_role('admin')
def admin_promote_user():
    data = request.get_json()
    user_id = data.get('user_id')
    new_role = data.get('role', 'manager')
    if not user_id:
        return jsonify({'success': False, 'message': 'Thiếu user_id'}), 400
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Không thể thay đổi quyền của chính mình'}), 400
    if new_role not in ['manager']:
        return jsonify({'success': False, 'message': 'Chỉ có thể thăng cấp lên manager'}), 400
    try:
        set_user_role(user_id, new_role, current_user.id, request.remote_addr, 'Promote User')
        return jsonify({'success': True, 'message': f'Thăng cấp người dùng lên {new_role} thành công'})
    except LookupError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except PermissionError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_user_bp.route('/api/admin/users/demote', methods=['POST'])
@require_role('admin')
def admin_demote_user():
    data = request.get_json()
    user_id = data.get('user_id')
    new_role = data.get('role', 'user')
    if not user_id:
        return jsonify({'success': False, 'message': 'Thiếu user_id'}), 400
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Không thể thay đổi quyền của chính mình'}), 400
    if new_role not in ['user']:
        return jsonify({'success': False, 'message': 'Chỉ có thể hạ cấp xuống user'}), 400
    try:
        set_user_role(user_id, new_role, current_user.id, request.remote_addr, 'Demote User')
        return jsonify({'success': True, 'message': f'Hạ cấp người dùng xuống {new_role} thành công'})
    except LookupError as e:
        return jsonify({'success': False, 'message': str(e)}), 404
    except PermissionError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_user_bp.route('/api/manager/users-permissions')
@require_role('manager')
def manager_get_users_permissions():
    try:
        users = db_manager.get_all_users_with_permissions()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
