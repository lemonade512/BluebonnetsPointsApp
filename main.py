"""`main` is the top level module for your Flask application."""

# Import the Flask Framework
from flask import Flask, request, redirect, render_template, url_for
app = Flask(__name__)
# Note: We don't need to call run() since our application is embedded within
# the App Engine WSGI application server.

from models import UserData

from functools import wraps

from google.appengine.api import users
from google.appengine.ext import ndb

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
#TODO make these show a more user friendly version of the error
# as opposed to just having some text on the page.
# TODO move this to a permissions.py library file
def require_permission(perm):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_data = get_current_user_data()
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

# TODO move this to UserData model and call it get user by user_id
def get_current_user_data():
    """ This function gets the current user's UserData or returns None """
    user = users.get_current_user()
    if user:
        #q = UserData.query().filter(UserData.user_id == user.user_id())
        #user_data = q.get()
        user_k = ndb.Key('UserData', user.user_id())
        user_data = user_k.get()
    else:
        user_data = None

    return user_data

@app.route('/login')
def login():
    cont = request.args.get("cont", "/")
    cont = url_for("postlogin", cont=cont)
    login_url = users.create_login_url(cont)
    return render_template("login.html", login_url=login_url)

@app.route('/signup')
def signup():
    cont = request.args.get("cont", "/")
    return render_template("signup.html", cont=cont)
    #return "Fill in the info to sign up!, Then going to " + request.args.get("cont", "/")

# TODO There might be an issue if the user logs into their google account then doesn't
# go through the signup process. Then if they click the back button a few times they will
# be logged into their google account but not have their UserData setup which could be
# an issue. Just make sure to be careful of that
@app.route('/postlogin')
def postlogin():
    """ Handler for just after a user has logged in

    This takes care of making sure the user has properly setup their account.
    """
    cont = request.args.get("cont", "/")
    user_data = get_current_user_data()
    if not user_data:
        # Need to create a user account
        signup_url = url_for("signup", cont=cont)
        return redirect(signup_url)
    else:
        return redirect(cont)

# TODO Right now when the user is redirected to the hello page they sometimes
# don't immediately see their name because the UserData object isn't yet
# consistent in the datastore. I need to figure out a way to fix this. I can
# either add an ancestor key for UserData objects or I can do some fancy client
# logic to keep the current UserData cached for a certain period of time.
# See http://stackoverflow.com/questions/11063597/read-delay-in-app-engine-datastore-after-put
@app.route('/createuser', methods=["POST"])
def createuser():
    print "Creating User"
    data = request.form
    user = users.get_current_user()
    if not user:
        raise Exception("Where is the user?")

    # NOTE: I am using the user.user_id() as the UserData id so that I can
    # query for UserData with strong consistency. I believe this works as
    # intended and the only issue I can think of is if I decide to allow
    # logging in from something other than a google account (which would mean
    # the user is not connected to a google user with a user_id)
    user_data = UserData(id=user.user_id())
    user_data.user = user
    user_data.user_id = user.user_id()
    user_data.first_name = data['fname']
    user_data.last_name = data['lname']
    #user_data.user_permissions = ['user', 'officer']
    user_data.user_permissions = ['user']
    user_data.put()

    # Return a '204: No Data' response. I believe this is how you handle
    # making server requests but I'm not sure...
    # I have figured out that the data gets passed to the client side handler
    # so it won't do anything with the browser but jquery could do something with
    # the data if it wanted to.
    return ('', '204')

@app.route('/')
def index():
    user = users.get_current_user()
    login_url = url_for('login', next=request.path)
    print "Login URL", login_url
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
    login_url = url_for('login', cont=request.path)
    return render_template("hello.html", user_data=user_data,
                           logout=users.create_logout_url("/"),
                           login=login_url)

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
