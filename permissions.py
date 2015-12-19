from models import UserData
from functools import wraps

from utils import render_jinja_template

#TODO allow multiple perms to be passed in through *args
def require_permission(perm):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_data = UserData.get_current_user_data()
            if not user_data:
                return render_jinja_template('nologin.html')

            if not check_perms(user_data, perm):
                template_values = {
                    'perms': [perm],
                }
                return render_jinja_template('nopermission.html', template_values)
            return f(*args, **kwargs)
        return wrapper
    return decorator

def check_perms(user_data, perm):
    if perm in user_data.user_permissions:
        return True

    return False

