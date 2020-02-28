from functools import wraps
from flask import abort
from flask_login import current_user

# 自定义修饰器，用于检查用户权限
def permissiong_required(permission):
    def decorator(f):
        @wrap(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_able(permission):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    return permissiong_required(Permission.ADMINISTER)(f)