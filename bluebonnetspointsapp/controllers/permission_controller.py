from flask import request, jsonify
from flask_restful import Resource
from permissions import require_permissions
from models.user_model import UserData

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
            # TODO (phillip): an officer could theoretically give themselves 'admin'
            # privileges using this function. They wouldn't get actual google
            # admin privileges but it would fool my permissions system
            user.user_permissions.append(perm)
        user.put()

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = "/api/users/" + user.user_id + \
                                       "/permissions/" + perm
        return response
