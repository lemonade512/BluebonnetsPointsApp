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
            #q = UserData.query().filter(UserData.user_id == user.user_id())
            #user_data = q.get()
            user_k = ndb.Key('UserData', user.user_id())
            user_data = user_k.get()
        else:
            user_data = None

        return user_data


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

