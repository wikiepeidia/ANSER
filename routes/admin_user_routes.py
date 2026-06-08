"""Admin and user-management routes — admin_user_bp Blueprint."""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from core.extensions import csrf, db_manager
from core.services.user_service import (
    admin_delete_user, delete_user, get_all_users,
    get_users_for_manager, reset_password, set_user_role,
)

admin_user_bp = Blueprint('admin_users', __name__)


@admin_user_bp.route('/api/admin/users')
@login_required
def admin_get_users():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    try:
        users = get_all_users()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_user_bp.route('/api/admin/activity')
@login_required
def admin_get_activity():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    activities = db_manager.get_recent_activities(limit=20)
    return jsonify({'success': True, 'activities': activities})


@admin_user_bp.route('/api/admin/stats')
@login_required
def admin_get_stats():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    return jsonify({'success': True, 'stats': {'users': 0, 'managers': 0, 'products': 0, 'customers': 0}})


@admin_user_bp.route('/api/admin/create-manager', methods=['POST'])
@login_required
def admin_create_manager():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
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
@login_required
def create_user():
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
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
@login_required
@csrf.exempt
def get_users():
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
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
@login_required
def delete_user_account(user_id):
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
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
@login_required
def reset_user_password(user_id):
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
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
@login_required
def admin_delete_user_route(user_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
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
@login_required
def admin_promote_user():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
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
@login_required
def admin_demote_user():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
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
@login_required
def manager_get_users_permissions():
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403
    try:
        users = db_manager.get_all_users_with_permissions()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
