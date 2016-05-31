"""`main` is the top level module for your Flask application."""

import logging
import json

from flask import Flask, request, redirect, url_for, jsonify
from flask_restful import Resource, Api
from google.appengine.api import users
from google.appengine.ext import deferred
from datetime import datetime

from models.user_model import UserData
from models.point_model import PointException, PointCategory, PointRecord
from models.event_model import Event
from utils.jinja import render_jinja_template
from permissions import require_permissions
from utils.update_schema import run_update_schema

# Create the flask app
app = Flask(__name__)
api = Api(app)

# *************************************************************************** #
#                               FLASK ROUTES                                  #
# *************************************************************************** #

@app.route('/')
def index():
    template_values = {
        'active_page': 'home',
        'target_user': UserData.get_current_user_data(),
    }
    if UserData.get_current_user_data():
        return render_jinja_template("dashboard.html", template_values)
    else:
        return render_jinja_template("index.html", template_values)


@app.route('/dashboard')
@app.route('/dashboard/<user_url_segment>')
@require_permissions(['self', 'officer'], logic='or')
def dashboard(user_url_segment=None):
    if user_url_segment is None:
        target_user = UserData.get_current_user_data()
    else:
        target_user = UserData.get_from_url_segment(user_url_segment)
    if target_user is None:
        template_values = {
            'target_user': user_url_segment,
        }
        return render_jinja_template("noprofile.html", template_values), 404

    if target_user.username != user_url_segment:
        return redirect('/dashboard/{0}'.format(target_user.username))

    # If looking at the current user's profile, hilight the users name in the
    # nav bar
    if target_user == UserData.get_current_user_data():
        return redirect('/'.format(target_user.username))
    else:
        active = None

    template_values = {
        'target_user': target_user,
    }
    return render_jinja_template("dashboard.html", template_values)

@app.route('/admin')
@require_permissions(['admin'])
def admin():
    template_values = {
        'active_page': 'admin',
    }
    return render_jinja_template("admin.html", template_values)

@app.route('/members')
@require_permissions(['officer'])
def members():
    template_values = {
        'active_page': 'members',
        'users': UserData.query().order(UserData.first_name),
    }

    return render_jinja_template("members.html", template_values)

@app.route('/permissions')
@require_permissions(['officer'])
def permissions():
    template_values = {
        'active_page': "permissions",
        'users': UserData.query().order(UserData.first_name),
    }

    return render_jinja_template("permissions.html", template_values)

# TODO (phillip): The only people who should be able to view a users profile page are
# officers and the user himself
@app.route('/profile/<user_url_segment>')
@require_permissions(['self', 'officer'], logic='or')
def profile(user_url_segment):
    target_user = UserData.get_from_url_segment(user_url_segment)
    if target_user is None:
        template_values = {
            'target_user': user_url_segment,
        }
        return render_jinja_template("noprofile.html", template_values), 404

    if target_user.username != user_url_segment:
        return redirect('/profile/{0}'.format(target_user.username))

    # If looking at the current user's profile, hilight the users name in the
    # nav bar
    if target_user == UserData.get_current_user_data():
        active = 'profile'
    else:
        active = None

    template_values = {
        'active_page': active,
        'target_user': target_user,
    }
    return render_jinja_template("profile.html", template_values)

@app.route('/login')
def login():
    next_url = url_for("postlogin", next=request.args.get("next", "/"))
    template_values = {
        'active_page': 'login',
        'google_login_url': users.create_login_url(next_url),
    }
    return render_jinja_template("login.html", template_values)

# TODO (phillip): There might be an issue if the user logs into their google account then doesn't
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

@app.route('/point-categories')
@require_permissions(['officer'])
def point_categories():
    template_values = {
        'active_page': 'point-categories',
    }
    return render_jinja_template('point-categories.html', template_values)

@app.route('/events')
@require_permissions(['officer'])
def event_list():
    template_values = {
        'active_page': 'events',
    }
    return render_jinja_template('events.html', template_values)

# TODO (phillip): handle the case when the event does not exist
@app.route('/events/<event>')
def event(event):
    event = Event.get_from_name(event)
    template_values = {
        'target_event': event,
    }
    return render_jinja_template('event.html', template_values)

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
    template_values = {
        'msg': "Sorry, unexpected error: {}".format(e)
    }
    return render_jinja_template("500.html", template_values), 500


# *************************************************************************** #
#                               REST API ENDPOINTS                            #
# *************************************************************************** #
from controllers.event_controller import EventAPI, EventListAPI
from controllers.exception_controller import ExceptionAPI, ExceptionListAPI
from controllers.permission_controller import PermissionAPI, PermissionListAPI
from controllers.point_controller import PointRecordAPI, PointCategoryAPI, PointCategoryListAPI
from controllers.user_controller import UserAPI, UserListAPI, UserPointsAPI

api.add_resource(UserListAPI, '/api/users', endpoint='users')
api.add_resource(UserAPI, '/api/users/<string:user_id>', endpoint='user')
api.add_resource(ExceptionListAPI, '/api/users/<string:user_id>/point-exceptions')
api.add_resource(ExceptionAPI, '/api/users/<string:user_id>/point-exceptions/<int:index>')
api.add_resource(PermissionListAPI, '/api/users/<string:user_id>/permissions')
api.add_resource(PermissionAPI, '/api/users/<string:user_id>/permissions/<string:perm>')
api.add_resource(PointCategoryListAPI, '/api/point-categories')
api.add_resource(PointCategoryAPI, '/api/point-categories/<string:name>')
api.add_resource(EventListAPI, '/api/events')
api.add_resource(EventAPI, '/api/events/<string:event>')
api.add_resource(PointRecordAPI, '/api/point-records')
api.add_resource(UserPointsAPI, '/api/users/<string:user_id>/points')


# *************************************************************************** #
#                               ADMIN                                         #
# *************************************************************************** #

@app.route("/admin/updateschema")
def updateschema():
    # NOTE: Sometimes there can be issues with the prerendering done by the
    # chrome address bar. In that case, you might see duplicate GET requests.
    # Be very aware of this when updating schema or going to endpoints that
    # could potentially destroy user data.
    deferred.defer(run_update_schema)
    return 'Schema migration successfully initiated.'

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.debug)

