"""`main` is the top level module for your Flask application."""

import logging
import json

from flask import Flask, request, redirect, url_for, jsonify
from flask_restful import Resource, Api
from google.appengine.api import users
from google.appengine.ext import deferred

from models import UserData, PointException
from utils import render_jinja_template
from permissions import require_permission, require_admin
from update_schema import run_update_schema

# Create the flask app
app = Flask(__name__)
api = Api(app)

@app.route('/')
def index():
    return render_jinja_template("index.html")

@app.route('/admin')
@require_admin
def admin():
    return render_jinja_template("admin.html")

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
        template_values = {
            "target_user": user_url_segment,
        }
        return render_jinja_template("noprofile.html", template_values), 404

    if target_user.username != user_url_segment:
        return redirect('/profile/{0}'.format(target_user.username))

    template_values = {
        'target_user': target_user,
    }
    return render_jinja_template("profile.html", template_values)

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

@app.route('/dashboard')
# Require user to be logged in
# TODO make a require_login decorator that redirects differently than require
# permission.
@require_permission('user')
def dashboard():
    template_values = {
        'active_page': 'dashboard',
    }
    return render_jinja_template("dashboard.html", template_values)

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
#                               API                                           #
# *************************************************************************** #

class UserListAPI(Resource):

    def get(self):
        user_filter = request.args.get("filter", "both")
        if user_filter not in ["active", "inactive", "both"]:
            raise Exception(user_filter + " is not a valid filter value")

        if user_filter == "active":
            q = UserData.query().filter(UserData.active == True)
        elif user_filter == "inactive":
            q = UserData.query().filter(UserData.active == False)
        else:
            q =  UserData.query()

        q = q.order(UserData.first_name)

        data = {"users":[]}
        for u in q:
            data['users'].append({
                "fname": u.first_name,
                "lname": u.last_name,
                "active": u.active,
                "grad_year": u.graduation_year,
                "grad_semester": u.graduation_semester,
                "classification": u.classification,
                "profile": "/profile/" + u.user_id,
            })

        return jsonify(**data)

    def post(self):
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

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = '/users/' + str(user_data.user_id)
        return response


# TODO possibly allow for using username in place of user_id
class UserAPI(Resource):

    def get(self, user_id):
        user = UserData.get_user_from_id(user_id)
        data = {
            "fname": user.first_name,
            "lname": user.last_name,
            "profile": "/profile/" + user.user_id,
            "point_exceptions": [{
                "point_type": exc.point_type,
                "points_needed": exc.points_needed,
            } for exc in user.point_exceptions],
        }

        return jsonify(**data)

    def put(self, user_id):
        # TODO check that the current user is either the target user or an officer
        user = UserData.get_user_from_id(user_id)
        if not user:
            raise Exception("I don't know that person")

        data = request.form
        user.first_name = data['fname']
        user.last_name = data['lname']
        if data['is_active'] == "true":
            user.active = True
        else:
            user.active = False
        user.classification = data['classification']
        user.graduation_semester = data['grad_semester']
        user.graduation_year = data.get('grad_year', type=int)
        user.put()

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = '/users/' + str(user.user_id)
        return response


class ExceptionAPI(Resource):

    def get(self, user_id, index):
        user = UserData.get_user_from_id(user_id)
        if not user:
            raise Exception("I don't know that person")

        if index > len(user.point_exceptions):
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        exc = user.point_exceptions[index]
        data = {
            "point_type": exc.point_type,
            "points_needed": exc.points_needed,
        }

        return jsonify(**data)

    # TODO delete needs to be idempotent
    def delete(self, user_id, index):
        user = UserData.get_user_from_id(user_id)
        if not user:
            raise Exception("I don't know that person")

        del user.point_exceptions[index]
        user.put()

        return ('', '204')


class ExceptionListAPI(Resource):

    def get(self, user_id):
        user = UserData.get_user_from_id(user_id)
        data = {
            "point_exceptions": [{
                "point_type": exc.point_type,
                "points_needed": exc.points_needed,
            } for exc in user.point_exceptions],
        }

        return jsonify(**data)

    def post(self, user_id):
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

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = "/users/" + user.user_id + "/point-exceptions/" + str(len(user.point_exceptions) - 1)
        return response


api.add_resource(UserListAPI, '/users', endpoint='users')
api.add_resource(UserAPI, '/users/<string:user_id>', endpoint='user')
api.add_resource(ExceptionListAPI, '/users/<string:user_id>/point-exceptions')
api.add_resource(ExceptionAPI, '/users/<string:user_id>/point-exceptions/<int:index>')


# *************************************************************************** #
#                               ADMIN                                         #
# *************************************************************************** #

@app.route("/admin/updateschema")
def updateschema():
    deferred.defer(run_update_schema)
    return 'Schema migration successfully initiated.'

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.debug)

