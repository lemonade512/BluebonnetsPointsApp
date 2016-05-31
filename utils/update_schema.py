import logging

from google.appengine.ext import ndb
from google.appengine.ext import deferred

from models.user_model import UserData
from models.point_model import PointCategory

BATCH_SIZE = 100  # ideal batch size may vary based on entity size.

def run_update_schema(cursor=None, num_updated=0):
    q = UserData.query()
    user_list, cur, _ = q.fetch_page(BATCH_SIZE, start_cursor=cursor)

    to_put = []
    for u in user_list:
        # In this example, the default values of 0 for num_votes and avg_rating
        # are acceptable, so we don't need this loop.  If we wanted to manually
        # manipulate property values, it might go something like this:
        to_put.append(u)

    if to_put:
        ndb.put_multi(to_put)
        num_updated += len(to_put)
        logging.debug(
            'Put %d entities to Datastore for a total of %d',
            len(to_put), num_updated)
        deferred.defer(run_update_schema, cursor=cur, num_updated=num_updated)
    else:
        logging.debug(
            'UpdateSchema complete with %d updates!', num_updated)


