from models import UserData
from functools import wraps

#TODO allow multiple perms to be passed in through *args
#TODO make these show a more user friendly version of the error
# as opposed to just having some text on the page.
# TODO move this to a permissions.py library file
def require_permission(perm):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_data = UserData.get_current_user_data()
            if not user_data:
                return "Must be logged in!!!!"

            if not check_perms(user_data, perm):
                return "Do not have the following permission: " + str(perm)
            f(*args, **kwargs)
        return wrapper
    return decorator

# TODO move this to a permissions.py library file
def check_perms(user_data, perm):
    if perm in user_data.user_permissions:
        return True

    return False

