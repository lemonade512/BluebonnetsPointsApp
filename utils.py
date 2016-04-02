from flask import render_template, url_for, request
from google.appengine.api import users

from models import UserData

def render_jinja_template(name, context=None):
    """ Renders a jinja template witha given context

    This function will also add global template values.

    Args:
        name: The name of the jinja template to be rendered
        context (dict): A dictionary of values to pass to the template
    """
    # We want to make sure all templates have this function, but we also
    # need to avoid circular dependencies so import this here.
    from permissions import check_perms

    template_values = {
        'user_data': UserData.get_current_user_data(),
        'login_url': url_for('login', next=request.path),
        'logout_url': users.create_logout_url("/"),
        'check_perms': check_perms,
    }

    if context != None:
        template_values.update(context)

    return render_template(name, **template_values)
