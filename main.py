"""`main` is the top level module for your Flask application."""

# Import the Flask Framework
from flask import Flask, request, redirect, render_template
app = Flask(__name__)
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

from models import UserData

from functools import wraps

from google.appengine.api import users


# Flask example of login_required
#from functools import wraps
#from flask import g, request, redirect, url_for
#
#def login_required(f):
#    @wraps(f)
#    def decorated_function(*args, **kwargs):
#        if g.user is None:
#            return redirect(url_for('login', next=request.url))
#        return f(*args, **kwargs)
#    return decorated_function

#TODO allow multiple perms to be passed in through *args
def require_permission(perm):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            print "IN WRAPPER"
            user_data = get_current_user_data()
            if not user_data:
                return "Must be logged in!!!!"

            if not check_perms(user_data, perm):
                return "Do not have the following permission: " + str(perm)
            f(*args, **kwargs)
        return wrapper
    return decorator

def check_perms(user_data, perm):
    if perm in user_data.user_permissions:
        return True

    return False

def get_current_user_data():
    """ This function gets the current user's UserData or returns None """
    user = users.get_current_user()
    if user:
        q = UserData.query().filter(UserData.user_id == user.user_id())
        user_data = q.get()

        if not user_data:
            # TODO need to create a function that redirects the user to a
            # registration page then redirects back to the page they were on.
            user_data = UserData()
            user_data.user = user
            user_data.user_id = user.user_id()
            user_data.first_name = user.nickname()
            user_data.last_name = "Last"
            #user_data.user_permissions = ['user', 'officer']
            user_data.user_permissions = ['user']
            user_data.put()
    else:
        user_data = None

    return user_data

@app.route('/')
def index():
    user = users.get_current_user()
    return render_template("index.html", user=user, logout=users.create_logout_url("/"))

@app.route('/admin')
def admin():
    #return "Welcome to the admin screen!"
    user = users.get_current_user()
    return render_template("admin.html", user=user, logout=users.create_logout_url("/"))

@app.route('/hello')
def hello():
    """ Return a friendly HTTP greeting. """
    user_data = get_current_user_data()
    return render_template("hello.html", user_data=user_data, logout=users.create_logout_url("/"))

    #user = users.get_current_user()
    #if user:
    #    return "Hello " + user.nickname()
    #else:
    #    return redirect(users.create_login_url(request.url))

# NOTE this is a way for me to do some basic testing of the permissions system
# NOTE the route decorator must be first so it decorates the function returned by
# any decorators following.
@app.route('/hello-perm')
@require_permission('officer')
def hello_perm():
    """ Check if officer then show page. """
    user_data = get_current_user_data()
    return render_template("hello.html", user_data=user_data, logout=users.create_logout_url("/"))


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


#@app.errorhandler(500)
#def application_error(e):
#    """Return a custom 500 error."""
#    return 'Sorry, unexpected error: {}'.format(e), 500
