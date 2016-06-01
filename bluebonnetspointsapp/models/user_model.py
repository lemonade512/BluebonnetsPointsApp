from google.appengine.ext import ndb
from google.appengine.api import users
import urlparse
from .point_model import PointException, PointRecord
from .event_model import Event

DEFAULT_ROOT_KEY = "default_root_key"

class UserData(ndb.Model):
    # Use a user_id instead of a UserProperty
    # https://cloud.google.com/appengine/docs/python/users/userobjects
    user_id = ndb.StringProperty()

    # Canonical reference to the user entity. Avoid referencing this directly
    # as the fields of this property can change; only the ID is stable and
    # userid can be used as a unique identifier instead. See the following
    # for further info https://cloud.google.com/appengine/articles/auth?hl=en
    # TODO (phillip): do we actually need to index user? I don't think we should ever
    # use it in a query.
    user = ndb.UserProperty(indexed=True)

    # Need a name for the user so they can be easily identified by officers
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()

    # Current bluebonnets are active. Past members are inactive (but still
    # available in the datastore if they are needed again)
    active = ndb.BooleanProperty()

    # What year the member is currently classified as (freshman, ...)
    classification = ndb.StringProperty(
        choices=['freshman', 'sophomore', 'junior', 'senior'])

    # The semester a member will be graduation (spring, fall)
    graduation_semester = ndb.StringProperty(
        choices=['spring', 'fall'])

    # The year a member is graduating (2016, 2017, ...)
    graduation_year = ndb.IntegerProperty()

    # Exceptions to the number of points a member needs
    point_exceptions = ndb.StructuredProperty(PointException, repeated=True)

    # The permissions that this user has. This is a list of strings that could
    # be "user" or "officer"
    user_permissions = ndb.StringProperty(repeated=True)

    def populate_records(self):
        # Create a PointRecord for every event with this user
        events = Event.query()
        for event in events:
            if PointRecord.query(PointRecord.event_name == event.name,
                                 PointRecord.username == self.username).get() is not None:
                # There is already a record for this event and this user
                continue

            new_record = PointRecord()
            new_record.username = self.username
            new_record.event_name = event.name
            new_record.put()

    @staticmethod
    def get_from_url_segment(url_segment):
        # TODO (phillip): this flow is a bit weird. There is theoretically a problem if a
        # a user_id is the same as a username because it will get the user with
        # the id before anything else.
        # TODO (phillip): Instead we could save the user_id and key as 'id_' + user.user_id()
        # (i.e. we have the id_ prefix and can check for that in the url_segment)
        if url_segment == "me":
            return UserData.get_user_from_id(users.get_current_user().user_id())

        user_data = UserData.get_user_from_id(url_segment)
        if not user_data:
            user_data = UserData.get_from_username(url_segment)

        return user_data

    # TODO (phillip): when creating users we need a way to ensure unique usernames that
    # are generated using the user's first and last name
    @property
    def username(self):
        return self.first_name + self.last_name

    @property
    def point_records(self):
        #return PointRecord.query().filter(PointRecord.user_data == self.key)
        return PointRecord.query(ancestory=self.key).filter(PointRecord.username == self.username)

    @staticmethod
    def get_current_user_data():
        """ This function gets the current user's UserData or returns None

        This function uses the key for the UserData object which means it
        is strongly consistent.
        """
        user = users.get_current_user()
        if user:
            user_data = UserData.get_user_from_id(user.user_id())
        else:
            user_data = None

        return user_data

    @staticmethod
    def get_from_username(username):
        # TODO (phillip): this method sucks
        # TODO (phillip): this is not strongly consistent because users are not stored in
        # an entity group and we are not querying by key only.
        q = UserData.query()
        for u in q:
            if u.username == username:
                return u

        return None

    @staticmethod
    def get_user_from_id(uid):
        user_k = ndb.Key('UserData', uid)
        return user_k.get()

    # TODO (phillip): implement this method!
    def is_baby(self):
        return False

