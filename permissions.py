from google.appengine.api import users

from models import UserData
from functools import wraps
from flask import jsonify

from utils import render_jinja_template

# TODO document somewhere what permissions are allowed
# Possible permissions:
#   * user - A logged in user
#   * officer - An officer
#   * self - function must have a user_id passed in as a keyword argument and
#       the user_id must match the current user
#   * other - function must have a user_id passed in as a keyword argument and
#       the user_id must be different than the current user

# TODO This function is a bit hacky but it works and it makes it easy
# to specify nice looking permissions decorators for any endpoint
def require_permissions(perms, logic='and', output_format='html'):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            current_user = UserData.get_current_user_data()
            if not current_user:
                template_values = {
                    u'message': u"Not logged in",
                    u'html_template': u"nologin.html",
                }
                return build_response(output_format, template_values)

            missing_perms = []
            if 'user_url_segment' in kwargs:
                other_user_url_segment = kwargs['user_url_segment']
            elif 'user_id' in kwargs:
                other_user_url_segment = kwargs['user_id']
            else:
                other_user_url_segment = None

            if other_user_url_segment:
                other_user = UserData.get_from_url_segment(other_user_url_segment)
            else:
                other_user = None

            for p in perms:
                if not check_perms(current_user, p, other_user):
                    missing_perms.append(p)

            template_values = {
                u'message': "Don't have permission",
                u'html_template': "nopermission.html",
                u'perms': missing_perms,
            }
            if len(missing_perms) > 0 and logic == 'and':
                return build_response(output_format, template_values)
            elif len(missing_perms) == len(perms) and logic == 'or':
                return build_response(output_format, template_values)

            return f(*args, **kwargs)
        return wrapper
    return decorator

def build_response(response_format, template_values):
    html_template = template_values['html_template']
    del template_values['html_template']

    if response_format == 'json':
        response = jsonify(**template_values)
        response.status_code = 403
        return response
    elif response_format == 'html':
        return render_jinja_template(html_template,
                                     template_values), 403
    else:
        raise Exception("Invalid response format")

def check_perms(user_data, perm, other_user=None):
    # Admins can do anything
    if users.is_current_user_admin():
        return True

    if perm in user_data.user_permissions:
        return True

    if perm == 'self' and user_data == other_user:
        return True

    # TODO This allows a user to access a page that does not have a target
    # user but still requires the 'self' permission. The weirdness of this
    # and determining the 'other_user' by special case might be indicative
    # of a deeper problem that needs to be fixed with permissions.
    if perm == 'self' and other_user is None:
        return True

    if perm == 'other' and user_data != other_user:
        return True

    return False

