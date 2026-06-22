"""User management business logic — extracted from admin_user_routes."""
from core.extensions import db_manager
from core.auth import AuthManager

def get_all_users(role_filter=None):
    return db_manager.get_all_users(role_filter)


def get_users_for_manager(manager_id, role_filter=None):
    return db_manager.get_users_for_manager(manager_id, role_filter)


def delete_user(user_id):
    """Delete a regular (role='user') account. Raises LookupError/PermissionError."""
    user = db_manager.get_user_by_id(user_id)
    if not user:
        raise LookupError('User not found')
    if user['role'] != 'user':
        raise PermissionError('Can only delete regular users')
    return db_manager.delete_user(user_id)


def admin_delete_user(user_id):
    """Admin-level deletion (any role). Raises LookupError if not found."""
    if not db_manager.delete_user(user_id):
        raise LookupError('User not found')


def reset_password(user_id, new_password):
    user = db_manager.get_user_by_id(user_id)
    if not user:
        raise LookupError('User not found')
    
    hashed_pw = AuthManager.hash_password(new_password)
    return db_manager.update_password(user_id, hashed_pw, version=1)


def set_user_role(user_id, new_role, actor_id, actor_ip, action_label):
    """Change a user's role. Validates the target is not an admin."""
    user = db_manager.get_user_by_id(user_id)
    if not user:
        raise LookupError('User not found')
    if user['role'] == 'admin':
        raise PermissionError('Cannot change admin role')
    
    db_manager.set_user_role(user_id, new_role)
    db_manager.log_activity(actor_id, action_label,
                            f'{action_label} user {user_id} to {new_role}', actor_ip)
