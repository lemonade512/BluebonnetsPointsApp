
from flask import request, jsonify
from flask_restful import Resource
from permissions import require_permissions
from models.user_model import UserData
from models.point_model import PointException

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

    # TODO (phillip): delete needs to be idempotent
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

        #TODO (phillip): The flow of this code looks more complicated and confusing than it
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
