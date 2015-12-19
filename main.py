"""`main` is the top level module for your Flask application."""

import logging

from flask import Flask, request, redirect, url_for
from google.appengine.api import users

from models import UserData
from utils import render_jinja_template
from permissions import require_permission

# Create the flask app
app = Flask(__name__)

@app.route('/')
def index():
    return render_jinja_template("index.html")

@app.route('/admin')
def admin():
    return render_jinja_template("admin.html")

@app.route('/hello')
def hello():
    """ Return a friendly HTTP greeting. """
    return render_jinja_template("hello.html")

# NOTE the route decorator must be first so it decorates the function returned by
# any decorators following.
@app.route('/hello-perm')
@require_permission('officer')
def hello_perm():
    """ Check if officer then show page. """
    return render_jinja_template("hello.html")

@app.route('/login')
def login():
    next_url = url_for("postlogin", next=request.args.get("next", "/"))
    template_values = {
        'google_login_url': users.create_login_url(next_url),
    }
    return render_jinja_template("login.html", template_values)

# TODO There might be an issue if the user logs into their google account then doesn't
# go through the signup process. Then if they click the back button a few times they will
# be logged into their google account but not have their UserData setup which could be
# an issue. Just make sure to be careful of that
@app.route('/postlogin')
def postlogin():
    """ Handler for just after a user has logged in

    This takes care of making sure the user has properly setup their account.
    """
    next_url = request.args.get("next", "/")
    user_data = UserData.get_current_user_data()
    if not user_data:
        # Need to create a user account
        signup_url = url_for("signup", next=next_url)
        return redirect(signup_url)
    else:
        return redirect(next_url)

@app.route('/signup')
def signup():
    template_values = {
        'next': request.args.get("next", "/"),
    }
    return render_jinja_template("signup.html", template_values)


# **************************************************************************** #
#                              Error Handlers                                  #
# **************************************************************************** #

@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return render_jinja_template("404.html"), 404

@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500


# *************************************************************************** #
#                               API                                           #
# *************************************************************************** #

@app.route('/createuser', methods=["POST"])
def createuser():
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

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.debug)
