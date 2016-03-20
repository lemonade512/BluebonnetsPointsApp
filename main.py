"""`main` is the top level module for your Flask application."""

import logging
import json

from flask import Flask, request, redirect, url_for, jsonify
from flask_restful import Resource, Api
from google.appengine.api import users
from google.appengine.ext import deferred
from datetime import datetime

from models import UserData, PointException, PointCategory, Event, PointRecord
from utils import render_jinja_template
from permissions import require_permissions
from update_schema import run_update_schema

# Create the flask app
app = Flask(__name__)
api = Api(app)

@app.route('/')
def index():
    template_values = {
        'active_page': 'home',
    }
    if UserData.get_current_user_data():
        return render_jinja_template("dashboard.html", template_values)
    else:
        return render_jinja_template("index.html", template_values)

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

# TODO The only people who should be able to view a users profile page are
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
@require_permissions(['user'])
def dashboard():
    return redirect(url_for("index"))

@app.route('/point-categories')
@require_permissions(['officer'])
def point_categories():
    return render_jinja_template('point-categories.html')

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

# TODO I need to return the proper error response when a request does not
# contain the proper data. See http://stackoverflow.com/questions/3050518/what-http-status-response-code-should-i-use-if-the-request-is-missing-a-required

class UserListAPI(Resource):

    @require_permissions(['officer'], output_format='json')
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
            # TODO code to create a user json object is duplicated in multiple
            # places. I should keep it in one spot (maybe UserData)
            data['users'].append({
                "fname": u.first_name,
                "lname": u.last_name,
                "active": u.active,
                "grad_year": u.graduation_year,
                "grad_semester": u.graduation_semester,
                "classification": u.classification,
                "permissions": u.user_permissions,
                "user_id": u.user_id,
            })

        return jsonify(**data)

    def post(self):
        """ Adds a new user

        This does not need any extra security because it only changes the
        information for the currently logged in google user. If there is no
        google user logged in an error is thrown.
        """
        # TODO this method throws generic exceptions that really can't be
        # properly handled by the client in a user-friendly way. I should
        # really return error codes here so the client knows what went wrong
        # other than a generic server error
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
        if data['fname'] == "":
            raise Exception("The first name was empty")
        user_data.first_name = data['fname']
        if data['lname'] == "":
            raise Exception("The first name was empty")

        # TODO A duplicate username should produce a better error than a 500
        other_users = UserData.query()
        other_user = None
        for user in other_users:
            if user.username == data['fname'] + data['lname']:
                other_user = user
        if other_user is not None:
            raise Exception("There is already a user with that name.")

        user_data.last_name = data['lname']
        user_data.graduation_year = int(data['grad_year'])
        user_data.graduation_semester = data['grad_semester']
        user_data.classification = data['classification']
        user_data.active = True
        user_data.user_permissions = ['user']
        user_data.put()

        # TODO find a better way that doesn't require you to remember to add
        # this line every single time you want to create a UserData object.
        # Create the necessary point records
        user_data.populate_records()

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = '/api/users/' + str(user_data.user_id)
        return response


# TODO possibly allow for using username in place of user_id
class UserAPI(Resource):

    @require_permissions(['self', 'officer'], output_format='json', logic='or')
    def get(self, user_id):
        user = UserData.get_user_from_id(user_id)
        data = {
            "active": user.active,
            "classification": user.classification,
            "grad_year": user.graduation_year,
            "grad_semester": user.graduation_semester,
            "fname": user.first_name,
            "lname": user.last_name,
            "permissions": user.user_permissions,
            "user_id": user.user_id,
            "point_exceptions": [{
                "point_category": exc.point_category,
                "points_needed": exc.points_needed,
            } for exc in user.point_exceptions],
        }

        return jsonify(**data)

    @require_permissions(['self', 'officer'], output_format='json', logic='or')
    def put(self, user_id):
        """ Updates the user profile information

        This method can only be called by the user being updated or an officer.
        We do not need to protect against the user changing their point
        exceptions in this method because the method does not update the point
        exceptions.
        """
        user = UserData.get_user_from_id(user_id)
        if not user:
            raise Exception("I don't know that person")

        data = request.form
        user.first_name = data['fname']
        user.last_name = data['lname']
        if data['active'] == "true":
            user.active = True
        else:
            user.active = False
        user.classification = data['classification']
        user.graduation_semester = data['grad_semester']
        user.graduation_year = data.get('grad_year', type=int)
        user.put()

        # TODO A put request (and really any other request that creates or
        # updates an object) should return the new representation of that
        # object so clients don't need to make more API calls

        response = jsonify()
        response.status_code = 204
        # TODO I believe only POST requests need to return this header
        response.headers['location'] = '/api/users/' + str(user.user_id)
        return response


class ExceptionAPI(Resource):

    @require_permissions(['self', 'officer'], output_format='json', logic='or')
    def get(self, user_id, index):
        user = UserData.get_user_from_id(user_id)
        if not user:
            raise Exception("I don't know that person")

        if index > len(user.point_exceptions)-1:
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        exc = user.point_exceptions[index]
        data = {
            "point_category": exc.point_category,
            "points_needed": exc.points_needed,
        }

        return jsonify(**data)

    # TODO delete needs to be idempotent
    @require_permissions(['other', 'officer'], output_format='json')
    def delete(self, user_id, index):
        user = UserData.get_user_from_id(user_id)
        if not user:
            raise Exception("I don't know that person")

        if index > len(user.point_exceptions)-1:
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        del user.point_exceptions[index]
        user.put()


class ExceptionListAPI(Resource):

    @require_permissions(['self', 'officer'], output_format='json', logic='or')
    def get(self, user_id):
        user = UserData.get_user_from_id(user_id)
        data = {
            "point_exceptions": [{
                "point_category": exc.point_category,
                "points_needed": exc.points_needed,
            } for exc in user.point_exceptions],
        }

        return jsonify(**data)

    @require_permissions(['other', 'officer'], output_format='json')
    def post(self, user_id):
        user = UserData.get_user_from_id(user_id)
        if not user:
            raise Exception("I don't know that person")

        #TODO The flow of this code looks more complicated and confusing than it
        # needs to be. Try to clean it up
        data = request.form
        p = None
        for exc in user.point_exceptions:
            if exc.point_category == data['point_category']:
                p = exc
        if not p:
            p = PointException()
            p.point_category = data.get('point_category', type=str)
            p.points_needed = data.get('points_needed', type=int)
            user.point_exceptions.append(p)
        else:
            p.points_needed = data.get('points_needed', type=int)
        user.put()

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = "/api/users/" + user.user_id + \
                                       "/point-exceptions/" + \
                                       str(user.point_exceptions.index(p))
        return response


class PermissionListAPI(Resource):

    @require_permissions(['officer'], output_format='json')
    def get(self, user_id):
        user = UserData.get_user_from_id(user_id)
        data = {
            u'permissions': user.user_permissions,
        }

        return jsonify(**data)

    @require_permissions(['officer'], output_format='json')
    def post(self, user_id):
        user = UserData.get_user_from_id(user_id)
        data = request.form
        perm = data['permission']
        if perm not in user.user_permissions:
            # TODO an officer could theoretically give themselves 'admin'
            # privileges using this function. They wouldn't get actual google
            # admin privileges but it would fool my permissions system
            user.user_permissions.append(perm)
        user.put()

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = "/api/users/" + user.user_id + \
                                       "/permissions/" + perm
        return response


class PermissionAPI(Resource):

    @require_permissions(['other', 'officer'], output_format='json')
    def delete(self, user_id, perm):
        user = UserData.get_user_from_id(user_id)
        if perm not in user.user_permissions:
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        user.user_permissions.remove(perm)
        user.put()


class PointCategoryListAPI(Resource):

    @require_permissions(['officer'], output_format='json')
    def get(self):
        point_categories = PointCategory.query(ancestor=PointCategory.root_key())
        out = {}
        for p in point_categories:
            if p.parent is None:
                out[p.name] = []
                invalid_keys = []
                for key in p.sub_categories:
                    sub = key.get()

                    # The key in sub_categories is no longer valid
                    if sub is None:
                        invalid_keys.append(key)
                    else:
                        out[p.name].append(sub.name)

                for key in invalid_keys:
                    p.sub_categories.remove(key)
                if invalid_keys:
                    p.put()

        return jsonify(**out)

    @require_permissions(['officer'], output_format='json')
    def post(self):
        """ Creates a new point category or updates a duplicate one

        If this function is given a point category with the same name as one
        that already exists, it will update the existing point category. It
        handles removing and adding necessary keys of parent categories.
        """
        data = request.form
        new_category = None
        new_key = None

        # TODO we shouldn't put anything in the datastore if there is an error.
        # Therefore, we should wait until the end of the function to call a
        # put if possible.

        # Check to see if the category already exists
        for category in PointCategory.query():
            if category.name == data['name']:
                new_category = category
                new_key = new_category.key

                parent = new_category.parent
                if parent is not None:
                    # Update old parent sub categories
                    parent.sub_categories.remove(new_key)
                    parent.put()

        # If the category doesn't exist, create a new one
        if not new_category:
            new_category = PointCategory(parent=PointCategory.root_key())
            new_category.name = data['name']
            new_key = new_category.put()

        # If necessary, add the proper key to the parent category
        parent = data.get('parent', None)
        # TODO Should I really also be checking for "none"? Is there a
        # better way?
        if parent is not None and parent != "none":
            parent = PointCategory.get_from_name(parent)
            parent.sub_categories.append(new_key)
            parent.put()

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = "/api/point-categories/" + new_category.name.replace(" ", "")
        return response


class PointCategoryAPI(Resource):

    def get(self, name):
        category = PointCategory.get_from_name(name)
        if category is None:
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        sub_categories = []
        for cat in category.sub_categories:
            sub_categories.append(cat.get().name)

        data = {
            "sub_categories": sub_categories,
            "name": category.name,
        }
        return jsonify(**data)


class EventListAPI(Resource):

    def get(self):
        """ Gets all events that have been created.

        URL Args:
            category (str): The category you want the events for. If category
                is 'all', then this will return all events. Any sub_categories
                will also be queried for events.
        """
        category = request.args.get("category", "all")
        if category == 'all':
            events = Event.query(ancestor=Event.root_key())
        else:
            category = PointCategory.get_from_name(category)
            if category is None:
                response = jsonify(message="Category does not exist")
                response.status_code = 404
                return response

            keys = []
            keys.append(category.key)
            keys.extend(category.sub_categories)

            events = Event.query(Event.point_category.IN(keys), ancestor=Event.root_key())

        events = events.order(Event.date)

        out = {'events': []}
        for event in events:
            out['events'].append({
                "name": event.name,
                "date": event.date,
                "point-category": event.point_category.get().name,
            })

        return jsonify(**out)

    @require_permissions(['officer'], output_format='json')
    def post(self):
        """ Creates a new event. """
        data = request.form
        new_category = None
        new_key = None

        # Don't allow duplicate events
        event = Event.get_from_name(data['name'])
        if event is not None:
            response = jsonify(message="Duplicate resource")
            response.status_code = 409
            return response

        # Get the point category by name
        point_category = PointCategory.get_from_name(data['point-category'])
        if point_category is None:
            raise Exception("Unknonwn point category: " + data['point-category'])

        new_event = Event(parent=Event.root_key())
        new_event.date = datetime.strptime(data['date'], "%Y-%m-%d")
        new_event.name = data['name']
        new_event.point_category = point_category.key
        new_event.put()

        # Make sure there are point records for this event
        new_event.populate_records()

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = "/api/events/" + new_event.name.replace(" ", "")
        return response


class EventAPI(Resource):

    def get(self, event):
        event = Event.get_from_name(event)
        if event is None:
            # TODO this code is duplicated, maybe make some sort of default
            # handler that can be called for any resource that doesn't exist?
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        out = {
            u'name': event.name,
            u'date': event.date,
            u'point-category': event.point_category.get().name,
        }
        return jsonify(**out)

    @require_permissions(['officer'], output_format='json')
    def delete(self, event):
        event = Event.get_from_name(event)
        if event is None:
            # TODO this code is duplicated, maybe make some sort of default
            # handler that can be called for any resource that doesn't exist?
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        event.delete()


class PointRecordAPI(Resource):

    # TODO write tests for this method
    def get(self):
        event_name = request.args.get("event_name", "all")
        username = request.args.get("username", "all")

        records = PointRecord.query()
        # TODO probably shouldn't make these special cases?
        if event_name != "all":
            records = records.filter(PointRecord.event_name == event_name)

        if username != "all":
            records = records.filter(PointRecord.username == username)

        out = {'records': []}
        for record in records:
            event = Event.get_from_name(record.event_name)
            if event is None:
                raise Exception("PointRecord with invalid event name")

            point_cat = event.point_category.get().name
            out['records'].append({
                'event_name': record.event_name,
                'username': record.username,
                'points-earned': record.points_earned,
                'point-category': point_cat,
            })

        return jsonify(**out)

    @require_permissions(['officer'], output_format='json')
    def put(self):
        data = request.form

        user_data = UserData.get_from_username(data['username'])
        if not user_data:
            raise Exception("I don't know that person")

        event = Event.get_from_name(data['event_name'])
        if not event:
            raise Exception("I don't know that event")

        point_record = PointRecord.query(PointRecord.event_name == event.name,
                                         PointRecord.username == user_data.username).get()
        # TODO this might allow me to not create new records every time a
        # new event or user is created because a record will be created when
        # the client tries to modify a record that should exist
        # Create a point record if one does not exist
        if not point_record:
            # TODO does this work with the user key as the ancestor?
            point_record = PointRecord(parent=user_data.key)

        point_record.event_name = event.name
        point_record.username = user_data.username
        point_record.points_earned = float(data['points-earned'])
        point_record.put()

        # TODO A put request (and really any other request that creates or
        # updates an object) should return the new representation of that
        # object so clients don't need to make more API calls

        response = jsonify()
        response.status_code = 204
        return response


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

