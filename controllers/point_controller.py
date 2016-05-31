from flask import request, jsonify
from flask_restful import Resource
from permissions import require_permissions
from models.user_model import UserData
from models.event_model import Event
from models.point_model import PointRecord, PointCategory, PointException

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

    def delete(self, name):
        category = PointCategory.get_from_name(name)
        if category is None:
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        category.key.delete();

    def patch(self, name):
        data = request.form
        baby_requirement = data.get('baby_requirement', None)
        member_requirement = data.get('member_requirement', None)

        category = PointCategory.get_from_name(name)
        if baby_requirement is not None:
            category.baby_requirement = int(baby_requirement)

        if member_requirement is not None:
            category.member_requirement = int(member_requirement)
        category.put()

        # TODO (phillip): A put request (and really any other request that creates or
        # updates an object) should return the new representation of that
        # object so clients don't need to make more API calls

        response = jsonify()
        response.status_code = 204
        return response


class PointCategoryListAPI(Resource):

    @require_permissions(['officer'], output_format='json')
    def get(self):
        point_categories = PointCategory.query(ancestor=PointCategory.root_key())
        out = {}
        for p in point_categories:
            if p.parent is None:
                out[p.name] = {
                    "name": p.name,
                    "baby_requirement": p.baby_requirement,
                    "member_requirement": p.member_requirement,
                    "sub_categories": [],
                }
                invalid_keys = []
                for key in p.sub_categories:
                    sub = key.get()

                    # The key in sub_categories is no longer valid
                    if sub is None:
                        invalid_keys.append(key)
                    else:
                        sub_cat = {
                            "name": sub.name,
                            "baby_requirement": sub.baby_requirement,
                            "member_requirement": sub.member_requirement,
                        }
                        out[p.name]['sub_categories'].append(sub_cat)

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

        # TODO (phillip): we shouldn't put anything in the datastore if there is an error.
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
        # TODO (phillip): Should I really also be checking for "none"? Is there a
        # better way?
        if parent is not None and parent != "none":
            parent = PointCategory.get_from_name(parent)
            parent.sub_categories.append(new_key)
            parent.put()

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = "/api/point-categories/" + new_category.name.replace(" ", "")
        return response

class PointRecordAPI(Resource):

    # TODO (phillip): write tests for this method
    def get(self):
        event_name = request.args.get("event_name", "all")
        username = request.args.get("username", "all")

        records = PointRecord.query()
        # TODO (phillip): probably shouldn't make these special cases?
        if event_name != "all":
            records = records.filter(PointRecord.event_name == event_name)

        if username != "all":
            records = records.filter(PointRecord.username == username)

        records = records.order(PointRecord.username)

        out = {'records': []}
        for record in records:
            event = Event.get_from_name(record.event_name)
            if event is None:
                logging.error("Tried to get a point record with an invalid event name: " + record.event_name)
                record.key.delete()
                continue

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
        # TODO (phillip): this might allow me to not create new records every time a
        # new event or user is created because a record will be created when
        # the client tries to modify a record that should exist
        # Create a point record if one does not exist
        if not point_record:
            # TODO (phillip): does this work with the user key as the ancestor?
            point_record = PointRecord(parent=user_data.key)

        point_record.event_name = event.name
        point_record.username = user_data.username
        point_record.points_earned = float(data['points-earned'])
        point_record.put()

        # TODO (phillip): A put request (and really any other request that creates or
        # updates an object) should return the new representation of that
        # object so clients don't need to make more API calls

        response = jsonify()
        response.status_code = 204
        return response

