from google.appengine.ext import ndb
from google.appengine.api import users
import urlparse

DEFAULT_ROOT_KEY = "default_root_key"


class PointCategory(ndb.Model):
    # The name of the point type (Sisterhood, Philanthropy, etc.)
    name = ndb.StringProperty()

    # A list of the sub-categories for this point type
    sub_categories = ndb.KeyProperty(kind="PointCategory", repeated=True)

    member_requirement = ndb.IntegerProperty()
    baby_requirement = ndb.IntegerProperty()

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
        # TODO (phillip): since this function ignores spaces in the PointCategory name,
        # I should make sure we can't make duplicate point categories after
        # spaces have been removed.
        q = PointCategory.query(ancestor=PointCategory.root_key())
        for p in q:
            if p.name.replace(" ", "") == name.replace(" ", ""):
                return p

        return None


class PointException(ndb.Model):
    """ A user-specific point exception """

    # The type of points to make an exception for
    # TODO (phillip): add a `choices` option to the string property depending on point
    # type options
    #point_category = ndb.StructuredProperty(PointCategory, indexed=False)
    point_category = ndb.StringProperty(indexed=False)

    # The number of points that will actually be needed
    points_needed = ndb.IntegerProperty(indexed=False)


# NOTE The UserData should be the parent entity of the PointRecord. This will
# allow you to have strong consistency without too much of a burden of 1 write
# per second in an entity group.
class PointRecord(ndb.Model):
    # TODO (phillip): find a way to use keys instead of strings, but for now this should
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

