from google.appengine.ext import ndb
from google.appengine.api import users

DEFAULT_ROOT_KEY = "default_root_key"


class PointCategory(ndb.Model):
    # The name of the point type (Sisterhood, Philanthropy, etc.)
    name = ndb.StringProperty()

    # A list of the sub-categories for this point type
    sub_categories = ndb.KeyProperty(kind="PointCategory", repeated=True)

    @staticmethod
    def root_key():
        """ Creates a root key for all point categories. """
        return ndb.Key("RootPointCategory", DEFAULT_ROOT_KEY)

    @property
    def parent(self):
        return PointCategory.query().filter(
            PointCategory.sub_categories.IN([self.key])).get()

    @staticmethod
    def get_from_name(name):
        """ Gets a point category matching the given name.

        The spaces in `name` are ignored in order to make urls look nicer
        without any spaces.
        """
        # TODO since this function ignores spaces in the PointCategory name,
        # I should make sure we can't make duplicate point categories after
        # spaces have been removed.
        q = PointCategory.query(ancestor=PointCategory.root_key())
        for p in q:
            if p.name.replace(" ", "") == name.replace(" ", ""):
                return p

        return None

# TODO do we actually need this class? Couldn't we just have the PointCategory
# keep track of its default requirements?
# NOTE: We probably do need this class (or something like it) to handle the
# case where babies have different requirements than full members.
class PointRequirement(ndb.Model):
    """ A global requirement for the number of points needed for a point type

    There should only ever be one of these for each point type. If someone
    tries adding a point requirement with a type that already has a point
    requirement it should cause an error.
    """
    point_category = ndb.StringProperty()
    points_needed = ndb.IntegerProperty(indexed=False)


class PointException(ndb.Model):
    """ A user-specific point exception """

    # The type of points to make an exception for
    # TODO add a `choices` option to the string property depending on point
    # type options
    #point_category = ndb.StructuredProperty(PointCategory, indexed=False)
    point_category = ndb.StringProperty(indexed=False)

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
        # TODO this flow is a bit weird. There is theoretically a problem if a
        # a user_id is the same as a username because it will get the user with
        # the id before anything else.
        # TODO Instead we could save the user_id and key as 'id_' + user.user_id()
        # (i.e. we have the id_ prefix and can check for that in the url_segment)
        if url_segment == "me":
            return UserData.get_user_from_id(users.get_current_user().user_id())

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
    # TODO find a way to use keys instead of strings, but for now this should
    # work just fine.
    username = ndb.StringProperty()
    event_name = ndb.StringProperty()
    #user_data = ndb.KeyProperty(kind="UserData")
    #event = ndb.KeyProperty(kind="Event")

    # NOTE: I believe we can just get the point category associated with the
    # event and not worry about keeping track of the PointCategory for a
    # PointRecord.
    #point_category = ndb.KeyProperty(kind="PointCategory")

    points_earned = ndb.FloatProperty()


# TODO how should I handle timezones? Also, how should I handle dates without
# times?
class Event(ndb.Model):
    name = ndb.StringProperty()
    date = ndb.DateTimeProperty()
    point_category = ndb.KeyProperty(kind="PointCategory")
    # TODO should I add an archived property?

    def populate_records(self):
        # Create point records for all users for this event
        users = UserData.query()
        for user in users:
            if PointRecord.query(PointRecord.event_name == self.name,
                                 PointRecord.username == user.username).get() is not None:
                # There is already a record for this event and this user
                continue

            new_record = PointRecord()
            new_record.username = user.username
            new_record.event_name = self.name
            new_record.put()

    def delete(self):
        """ Deletes self from the DataStore.

        Note: I tried overriding the __del__ method but ran into a bunch of
        problems, so use this method instead. If you try using the __del__
        method it may get called way more often than expected. I believe it
        is most likely used by appengine itself so be very careful.
        """

        # TODO test the deletion of PointRecords
        # Delete all PointRecords associated with this event
        q = PointRecord.query(PointRecord.event_name == self.name)
        for r in q:
            r.key.delete()

        # Delete the entity from the datastore.
        self.key.delete()

    @property
    def point_records(self):
        #return PointRecord.query().filter(PointRecord.event == self.key)
        return PointRecord.query().filter(PointRecord.event_name == self.name)

    @staticmethod
    def root_key():
        """ Creates a root key for all events. """
        # TODO having the same key for all events may be inefficient, so
        # at some point I should look into changing this.
        return ndb.Key("RootEvent", DEFAULT_ROOT_KEY)

    @staticmethod
    def get_from_name(name):
        """ Gets an event matching the given name.

        The spaces in `name` are ignored in order to make urls look nicer
        without any spaces.
        """
        q = Event.query(ancestor=Event.root_key())
        for e in q:
            if e.name.replace(" ", "") == name.replace(" ", ""):
                return e

        return None

