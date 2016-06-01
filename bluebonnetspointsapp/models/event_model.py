from google.appengine.ext import ndb
from google.appengine.api import users
import urlparse
from .point_model import PointRecord

# TODO: this only needs to be defined once
DEFAULT_ROOT_KEY = "default_root_key"

# TODO (phillip): how should I handle timezones? Also, how should I handle dates without
# times?
class Event(ndb.Model):
    name = ndb.StringProperty()
    date = ndb.DateTimeProperty()
    point_category = ndb.KeyProperty(kind="PointCategory")
    # TODO (phillip): should I add an archived property?

    def populate_records(self):
        # need to import here since UserData must be initialized first
        from .user_model import UserData
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

        # TODO (phillip): test the deletion of PointRecords
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
        # TODO (phillip): having the same key for all events may be inefficient, so
        # at some point I should look into changing this.
        return ndb.Key("RootEvent", DEFAULT_ROOT_KEY)

    @staticmethod
    def get_from_name(name):
        """ Gets an event matching the given name.

        The spaces in `name` are ignored in order to make urls look nicer
        without any spaces. Additionally, any url encoded characters are
        replaced with the proper characters (ex. %2F -> /)
        """
        name = urlparse.unquote(name)
        q = Event.query(ancestor=Event.root_key())
        for e in q:
            if e.name.replace(" ", "") == name.replace(" ", ""):
                return e

        return None

