from datetime import datetime
from flask import request, jsonify
from flask_restful import Resource
from permissions import require_permissions
from models.event_model import Event
from models.point_model import PointRecord, PointCategory

class EventAPI(Resource):

    def get(self, event):
        event = Event.get_from_name(event)
        if event is None:
            # TODO (phillip): this code is duplicated, maybe make some sort of default
            # handler that can be called for any resource that doesn't exist?
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        out = {
            u'name': event.name,
            u'date': event.date.strftime('%m/%d/%Y'),
            u'point-category': event.point_category.get().name,
        }
        return jsonify(**out)

    @require_permissions(['officer'], output_format='json')
    def delete(self, event):
        event = Event.get_from_name(event)
        if event is None:
            # TODO (phillip): this code is duplicated, maybe make some sort of default
            # handler that can be called for any resource that doesn't exist?
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        event.delete()

    def put(self, event):
        data = request.form

        new_event_name = data['name']
        dup_event = Event.get_from_name(new_event_name)
        # Don't allow duplicate events
        if dup_event is not None and new_event_name.replace(" ", "") != event.replace(" ", ""):
            response = jsonify(message="Duplicate resource")
            response.status_code = 409
            return response

        event = Event.get_from_name(event)
        if event is None:
            # TODO (phillip): this code is duplicated, maybe make some sort of default
            # handler that can be called for any resource that doesn't exist?
            response = jsonify(message="Resource does not exist")
            response.status_code = 404
            return response

        # Get the point category by name
        point_category = PointCategory.get_from_name(data['point-category'])
        if point_category is None:
            raise Exception("Unknonwn point category: " + data['point-category'])

        records = PointRecord.query(PointRecord.event_name == event.name)
        for record in records:
            record.event_name = data['name']
            record.put()

        event.name = data['name']
        event.date = datetime.strptime(data['date'], "%Y-%m-%d")
        event.point_category = point_category.key
        event.put()

        response = jsonify()
        response.status_code = 201
        response.headers['location'] = "/api/events/" + event.name.replace(" ", "")
        return response


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
                "date": event.date.strftime('%m/%d/%Y'),
                "point-category": event.point_category.get().name,
            })

        return jsonify(**out)

    @require_permissions(['officer'], output_format='json')
    def post(self):
        """ Creates a new event. """
        data = request.form

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

