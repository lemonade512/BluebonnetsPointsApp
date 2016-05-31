from flask import request, jsonify
from flask_restful import Resource
from permissions import require_permissions
from models.user_model import UserData
from models.event_model import Event
from models.point_model import PointRecord, PointCategory
from google.appengine.api import users
from google.appengine.ext import deferred

# TODO (phillip): possibly allow for using username in place of user_id
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

        # TODO (phillip): A put request (and really any other request that creates or
        # updates an object) should return the new representation of that
        # object so clients don't need to make more API calls

        response = jsonify()
        response.status_code = 204
        # TODO (phillip): I believe only POST requests need to return this header
        response.headers['location'] = '/api/users/' + str(user.user_id)
        return response


# Returns how many points the user needs for each category. This handles
# getting all point categories, getting any point exceptions, and using
# the correct requirement based on if the user is a baby or a full member.
# Eventually this will also carry information about how the user gained each
# point and how many community points the user has.
class UserPointsAPI(Resource):

    @staticmethod
    def reshape_categories(cat_info):
        """ Reshape flat list of catory information to include structure.

        Args:
            cat_info (dict): A flat dictionary of all categories, their point
                requirements, and their points earned.

        Returns:
            A structured dictionary with each category, its sub-categoires,
            points required, and points earned.
        """
        out = {}

        # TODO (phillip): this code is probably duplicated from the PointCategoryListAPI
        point_categories = PointCategory.query(ancestor=PointCategory.root_key())
        for cat in point_categories:
            if cat.parent is None:
                out[cat.name] = {
                    "required": cat_info['categories'][cat.name]['required'],
                    "received": cat_info['categories'][cat.name]['received'],
                    "level": 1,
                    "sub_categories": {},
                }

                invalid_keys = []
                for key in cat.sub_categories:
                    sub = key.get()

                    # The key in sub_categories is no longer valid
                    if sub is None:
                        invalid_keys.append(key)
                    else:
                        sub_cat = {
                            "required": cat_info['categories'][sub.name]['required'],
                            "received": cat_info['categories'][sub.name]['received'],
                            "level": 2,
                        }
                        out[cat.name]['sub_categories'][sub.name] = sub_cat

                for key in invalid_keys:
                    cat.sub_categories.remove(key)
                if invalid_keys:
                    cat.put()

        return out

    @require_permissions(['self', 'officer'], output_format='json', logic='or')
    def get(self, user_id):
        output = {
            u'categories': {}
        }

        user = UserData.get_user_from_id(user_id)

        point_exceptions = {exc.point_category: exc.points_needed for exc in user.point_exceptions}
        categories = PointCategory.query(ancestor=PointCategory.root_key())
        for cat in categories:
            # TODO (phillip): Write tests to test the behavior when calculating requirement for
            # a category with children having a higher requirement. (i.e. max(self, children))

            # TODO (phillip): remove some of the ugly repeated code below
            # Add each category and the required number of points
            if user.is_baby():
                requirement = cat.baby_requirement
                if requirement is None:
                    requirement = 0

                sub_req_list = []
                for sub in cat.sub_categories:
                    req = sub.get().member_requirement
                    if req is None:
                        sub_req_list.append(0)
                    else:
                        sub_req_list.append(req)
                sub_req = sum(sub_req_list)
                requirement = max(requirement, sub_req)
            else:
                requirement = cat.member_requirement
                if requirement is None:
                    requirement = 0

                # TODO (phillip): add test when one of the requirements is None
                sub_req_list = []
                for sub in cat.sub_categories:
                    req = sub.get().member_requirement
                    if req is None:
                        sub_req_list.append(0)
                    else:
                        sub_req_list.append(req)
                sub_req = sum(sub_req_list)
                requirement = max(requirement, sub_req)

            if cat.name in point_exceptions:
                requirement = point_exceptions[cat.name]

            output['categories'][cat.name] = {
                u'required': requirement,
            }


            output['categories'][cat.name]['received'] = 0
            if cat.parent is not None:
                output['categories'][cat.name]['level'] = 2
            else:
                output['categories'][cat.name]['level'] = 1

        # NOTE: At this point I am assuming each category has been added to
        # the output. If this is not true, the following code will fail
        # miserably.
        records = PointRecord.query()
        #username = user.username
        records = records.filter(PointRecord.username == user.username)
        for record in records:
            event = Event.get_from_name(record.event_name)
            if event is None:
                logging.error("Uknown event " + record.event_name + " requested for point record: " + str(record))
                record.key.delete()
                continue

            category = event.point_category.get()
            if record.points_earned is None:
                record.points_earned = 0
                record.put()
            output['categories'][category.name]['received'] += record.points_earned

            # Make sure to also count the points for the parent category
            if category.parent is not None:
                output['categories'][category.parent.name]['received'] += record.points_earned
                output['categories'][category.name]['level'] = 2

        output = self.reshape_categories(output)

        return jsonify(**output)

# TODO (phillip): I need to return the proper error response when a request does not
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
            # TODO (phillip): code to create a user json object is duplicated in multiple
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
        # TODO (phillip): this method throws generic exceptions that really can't be
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

        # TODO (phillip): A duplicate username should produce a better error than a 500
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

        # TODO (phillip): find a better way that doesn't require you to remember to add
        # this line every single time you want to create a UserData object.
        # Create the necessary point records
        user_data.populate_records()

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = '/api/users/' + str(user_data.user_id)
        return response

