from google.appengine.ext import ndb
from google.appengine.api import users

# TODO I need to figure out how to store point requirements in a way that
# officers can change them. One way would be to have a point requirements
# property in the UserData and then any time an officer updates the default
# point requirements it will update all of the member's point requirements
# fields. Another option is to just have a python file that is used to store
# the requirements. The downside with this is that I would have to deploy the
# site every time they want to change the point requirements.

class PointException(ndb.Model):

    # The type of points to make an exception for
    # TODO add a `choices` option to the string property depending on point
    # type options
    point_type = ndb.StringProperty(indexed=False)

    # The number of points that will actually be needed
    points_needed = ndb.IntegerProperty(indexed=False)


class UserData(ndb.Model):
    # Use a user_id instead of a UserProperty
    # https://cloud.google.com/appengine/docs/python/users/userobjects
    user_id = ndb.StringProperty()

    # Canonical reference to the user entity. Avoid referencing this directly
    # as the fields of this property can change; only the ID is stable and
    # userid can be used as a unique identifier instead. See the following
    # for further info https://cloud.google.com/appengine/articles/auth?hl=en
    # TODO do we actually need to index user? I don't think we should ever
    # use it in a query.
    user = ndb.UserProperty(indexed=True)

    # Need a name for the user so they can be easily identified by officers
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()

    # Current bluebonnets are active. Past members are inactive (but still
    # available in the datastore if they are needed again)
    active = ndb.BooleanProperty()

    # Exceptions to the number of points a member needs
    point_exceptions = ndb.StructuredProperty(PointException, repeated=True)

    # The permissions that this user has. This is a list of strings that could
    # be "user" or "officer"
    user_permissions = ndb.StringProperty(repeated=True)

    @staticmethod
    def get_from_url_segment(url_segment):
        # TODO this flow is a bit weird. There is theoretically a problem if a
        # a user_id is the same as a username because it will get the user with
        # the id before anything else.
        # TODO Instead we could save the user_id and key as 'id_' + user.user_id()
        # (i.e. we have the id_ prefix and can check for that in the url_segment)
        user_data = UserData.get_user_from_id(url_segment)
        if not user_data:
            user_data = UserData.get_from_username(url_segment)

        return user_data

    # TODO when creating users we need a way to ensure unique usernames that
    # are generated using the user's first and last name
    @property
    def username(self):
        return self.first_name + self.last_name

    @property
    def point_records(self):
        return PointRecord.query().filter(PointRecord.user_data == self.key)

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
        # TODO this method sucks
        # TODO this is not strongly consistent because users are not stored in
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


# NOTE The UserData should be the parent entity of the PointRecord. This will
# allow you to have strong consistency without too much of a burden of 1 write
# per second in an entity group.
class PointRecord(ndb.Model):
    user_data = ndb.KeyProperty(kind="UserData")
    event = ndb.KeyProperty(kind="Event")
    points_earned = ndb.IntegerProperty()
    point_type = ndb.StringProperty()


class Event(ndb.Model):
    event_name = ndb.StringProperty()
    event_date = ndb.DateTimeProperty()
    # TODO should I add an archived property?

    @property
    def point_records(self):
        return PointRecord.query().filter(PointRecord.event == self.key)

