"""`main` is the top level module for your Flask application."""

import logging
import json

from flask import Flask, request, redirect, url_for
from google.appengine.api import users

from models import UserData, PointException
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
    return render_jinja_template("hello.html")

@app.route('/members')
@require_permission('officer')
def members():
    # TODO right now I am getting all of the users on a server and then
    # rendering the template. It might be better to make an ajax request
    # to populate the data on the client. This would allow better
    # client-side error handling if data is missing (a page could still be
    # shown)
    template_values = {
        'users': UserData.query().order(UserData.first_name)
    }

    return render_jinja_template("members.html", template_values)

# TODO The only people who should be able to view a users profile page are
# officers and the user himself
@app.route('/profile/<user_url_segment>')
def profile(user_url_segment):
    target_user = UserData.get_from_url_segment(user_url_segment)
    if target_user is None:
        # TODO should I make this template more informative? Right now it just
        # says a user could not be found, not which user could not be found.
        # Although, I really don't know how to determine the user if the id
        # could not be found.
        return render_jinja_template("noprofile.html"), 404

    if target_user.username != user_url_segment:
        return redirect('/profile/{0}'.format(target_user.username))

    template_values = {
        'target_user': target_user,
    }
    return render_jinja_template("profile.html", template_values)

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

# TODO I am not following good REST standards. I should change that

@app.route('/updateuser', methods=["POST"])
def updateuser():
    # TODO check that the current user is either the target user or an officer
    data = request.form
    user = UserData.get_user_from_id(data['target_user_id'])
    if not user:
        raise Exception("I don't know that person")

    user.first_name = data['fname']
    user.last_name = data['lname']
    if data['is_active'] == "true":
        user.active = True
    else:
        user.active = False
    user.put()
    return ('', '204')

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
    user_data.active = True
    # TODO when we create a way to change permissions then this should not be
    # the default permission set
    user_data.user_permissions = ['user', 'officer']
    #user_data.user_permissions = ['user']
    user_data.put()

    # Return a '204: No Data' response. I believe this is how you handle
    # making server requests but I'm not sure...
    # I have figured out that the data gets passed to the client side handler
    # so it won't do anything with the browser but jquery could do something with
    # the data if it wanted to.
    return ('', '204')

@app.route('/getusers')
def getusers():
    # get param "filter="
    user_filter = request.args.get("filter")
    if user_filter not in ["active", "inactive", "both"]:
        raise Exception(user_filter + " is not a valid filter value")

    if user_filter == "active":
        q = UserData.query().filter(UserData.active == True)
    elif user_filter == "inactive":
        q = UserData.query().filter(UserData.active == False)
    else:
        q =  UserData.query()

    q = q.order(UserData.first_name)

    data = []
    for u in q:
        data.append({
            "fname": u.first_name,
            "lname": u.last_name,
            "profile": "/profile/" + u.user_id
        })

    json_data = json.dumps(data)
    return json_data

@app.route('/getpointexceptions')
def getpointexceptions():
    # get param "target_user_id="
    target_user_id = request.args.get("target_user_id")
    user = UserData.get_user_from_id(target_user_id)
    if not user:
        raise Exception("I don't know that person")

    data = []
    for exc in user.point_exceptions:
        data.append({
            "point_type": exc.point_type,
            "points_needed": exc.points_needed,
            "index": user.point_exceptions.index(exc),
        })

    json_data = json.dumps(data)
    return json_data

@app.route('/createpointexception', methods=['POST'])
def createpointexception():
    data = request.form
    user = UserData.get_user_from_id(data['target_user_id'])
    if not user:
        raise Exception("I don't know that person")

    #TODO The flow of this code looks more complicated and confusing than it
    # needs to be. Try to clean it up
    p = None
    for exc in user.point_exceptions:
        if exc.point_type == data['point_type']:
            p = exc
    if not p:
        p = PointException()
        p.point_type = data.get('point_type', type=str)
        p.points_needed = data.get('points_needed', type=int)
        user.point_exceptions.append(p)
    else:
        p.points_needed = data.get('points_needed', type=int)
    user.put()

    return ('', '204')

@app.route('/deletepointexception', methods=['POST'])
def deletepointexception():
    data = request.form
    target_user_id = data["target_user_id"]
    user = UserData.get_user_from_id(target_user_id)
    if not user:
        raise Exception("I don't know that person")

    del user.point_exceptions[int(data['index'])]
    user.put()

    return ('', '204')

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.debug)

