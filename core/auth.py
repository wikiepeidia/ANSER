"""Role-gating primitives for San Xuat's sensitive routes (SEC-01).

Only two role values are real anywhere in this codebase: `'manager'`
(`core/auth_db.py`'s manager-count query) and the default `'user'`
(`core/models.py::User.__init__`'s default). Callers should never invent
finer-grained role strings like `qc`/`kho`/`quan_ly` -- there is no data
model backing them. `require_role`/`user_has_role` accept `*roles` so this
stays extensible later without an API change, but today only
`require_role('manager')` / `user_has_role('manager')` are meaningful.

Role is read exclusively from `flask_login.current_user.role`, populated
server-side from the shared Gateway session (`core/auth_db.get_user_by_id`
-> `core/models.py::User`) -- never from request body/query params, so
there is no client-supplied-role spoofing surface.
"""
from functools import wraps

from flask import jsonify
from flask_login import current_user


def user_has_role(*roles):
    """True if the current session is authenticated AND its role is one of
    `roles`. False if unauthenticated or the role doesn't match."""
    return bool(current_user.is_authenticated) and getattr(current_user, 'role', None) in roles


def require_role(*roles):
    """Decorator: 403s with a standard message if `user_has_role(*roles)` is
    False, otherwise calls the wrapped view unchanged. Stack directly under
    `@login_required` (role-checking assumes authentication already ran)."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not user_has_role(*roles):
                return jsonify({'success': False, 'message': 'Không đủ quyền truy cập'}), 403
            return view(*args, **kwargs)
        return wrapped
    return decorator
