import unittest
import urllib
import json
import mock
import datetime

from google.appengine.ext import testbed
#from google.appengine.ext import ndb

import main
from models import UserData, PointException, PointCategory, Event, PointRecord


def setup_datastore():
    """ Sets up the testing datastore to test with dummy data. """
    # Point Categories
    bloob_time = PointCategory(parent=PointCategory.root_key())
    bloob_time.name = "Bloob Time"
    bloob_time.member_requirement = 10
    bloob_time_key = bloob_time.put()

    mixers = PointCategory(parent=PointCategory.root_key())
    mixers.name = "Mixers"
    mixers.member_requirement = 8
    mixers_key = mixers.put()

    sisterhood = PointCategory(parent=PointCategory.root_key())
    sisterhood.name="Sisterhood"
    sisterhood.member_requirement = 20
    sisterhood.sub_categories = [bloob_time_key, mixers_key]
    sisterhood_key = sisterhood.put()

    philanthropy = PointCategory(parent=PointCategory.root_key())
    philanthropy.name = "Philanthropy"
    philanthropy.member_requirement = 12
    philanthropy_key = philanthropy.put()

    # Point Exceptions
    mixers_exception = PointException()
    mixers_exception.point_category = "Mixers"
    mixers_exception.points_needed = 5

    # Users
    u = UserData(id='100')
    u.user_permissions = ['user']
    u.user_id = '100'
    u.active = True
    u.first_name = "Bill"
    u.last_name = "Gates"
    u.classification = "senior"
    u.graduation_year = 2015
    u.graduation_semester = "fall"
    u.point_exceptions = [
        mixers_exception
    ]
    u.put()

    u = UserData(id='101')
    u.user_permissions = ['user']
    u.user_id = '101'
    u.active = True
    u.first_name = "Jake"
    u.last_name = "Sisko"
    u.classification = "senior"
    u.graduation_year = 2015
    u.graduation_semester = "fall"
    u.point_exceptions = []
    u.put()

    u = UserData(id='200')
    u.user_permissions = ['user', 'officer']
    u.user_id = '200'
    u.active = False
    u.first_name = "Bob"
    u.last_name = "Joe"
    u.classification = "freshman"
    u.graduation_year = 2016
    u.graduation_semester = "spring"
    u.point_exceptions = [
        mixers_exception
    ]
    u.put()

    # Events
    e = Event(parent=Event.root_key())
    e.name = "My First Event"
    e.date = datetime.datetime(2016, 8, 3)
    e.point_category = philanthropy_key
    e.put()

    e = Event(parent=Event.root_key())
    e.name = "Habitat for Humanity"
    e.date = datetime.datetime(2016, 3, 4)
    e.point_category = philanthropy_key
    e.put()

    e = Event(parent=Event.root_key())
    e.name = "Sisterhood Event"
    e.date = datetime.datetime(2016, 8, 2)
    e.point_category = sisterhood_key
    e.put()

    e = Event(parent=Event.root_key())
    e.name = "Bloob Time Event"
    e.date = datetime.datetime(2016,9,1)
    e.point_category = bloob_time_key
    e.put()

    e = Event(parent=Event.root_key())
    e.name = "Mixers Event"
    e.date = datetime.datetime(2016,5,3)
    e.point_category = mixers_key
    e.put()

    # Point Records
    p = PointRecord()
    p.event_name = "Mixers Event"
    p.username = "BillGates"
    p.points_earned = 2
    p.put()

    p = PointRecord()
    p.event_name = "Sisterhood Event"
    p.username = "JakeSisko"
    p.points_earned = 1
    p.put()

    p = PointRecord()
    p.event_name = "Bloob Time Event"
    p.username = "JakeSisko"
    p.points_earned = 3
    p.put()

    # TODO use next two to test for multiple records of same category
    p = PointRecord()
    p.event_name = "Habitat for Humanity"
    p.username = "BobJoe"
    p.points_earned = 2
    p.put()

    p = PointRecord()
    p.event_name = "My First Event"
    p.username = "BobJoe"
    p.points_earned = 1
    p.put()


# TODO rename _testbed to something else
def setup_testbed():
    global _testbed
    _testbed = testbed.Testbed()
    _testbed.activate()
    _testbed.init_user_stub()
    _testbed.init_memcache_stub()
    _testbed.init_datastore_v3_stub()
    #ndb.get_context().clear_cache()
    setup_datastore()

def teardown_testbed():
    _testbed.deactivate()

def loginUser(email='user@example.com', user_id='123', is_admin=False):
    _testbed.setup_env(
        user_email=email,
        user_id=user_id,
        user_is_admin='1' if is_admin else '0',
        overwrite=True)

# TODO setUpModule and tearDownModule each only call one function which is dumb
def setUpModule():
    setup_testbed()

def tearDownModule():
    teardown_testbed()


#pylint: disable=too-many-public-methods
class MainTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = main.app.test_client()

    def setUp(self):
        # Make sure no user is logged in
        loginUser('', '')

    def test_logged_out_homepage(self):
        rv = self.app.get("/")
        self.assertEqual(200, rv.status_code)
        self.assertIn("Welcome to the main page!",
                      rv.data,
                      msg="Does not show proper welcome")

    @mock.patch('main.render_jinja_template')
    def test_logged_in_homepage(self, mock_jinja):
        mock_jinja.return_value = "Hello"
        loginUser(user_id='100')
        response = self.app.get("/")
        mock_jinja.assert_called_with('dashboard.html', {'active_page': 'home'})

    def test_members_page_off_limits_to_user(self):
        loginUser(user_id='100')
        response = self.app.get('/members')
        self.assertEqual(403, response.status_code)
        s = ("You need the following permissions to view that page:"
             " [&#39;officer&#39;]")
        self.assertIn(s, response.data, msg="Does not show necessary permissions")

    def test_members_page_available_to_officer(self):
        loginUser(user_id='200')
        response = self.app.get('/members')
        self.assertEqual(200, response.status_code)

    def test_admin_page_off_limits(self):
        loginUser(user_id='100', is_admin=False)
        response = self.app.get('/admin')
        self.assertEqual(403, response.status_code)
        s = ("You need the following permissions to view that page:"
             " [&#39;admin&#39;]")
        self.assertIn(s, response.data)

    def test_profile_redirect_to_username(self):
        loginUser(user_id='100')
        response = self.app.get('/profile/100')
        self.assertEqual(302, response.status_code)
        self.assertIn("<title>Redirecting...</title>", response.data)
        # TODO test a user with the same name being redirected to a different username
        self.assertEqual("http://localhost/profile/BillGates", response.headers['Location'])

    def test_profile_username_ok_status(self):
        loginUser(user_id="100")
        response = self.app.get('/profile/BillGates')
        self.assertEqual(200, response.status_code)

    def test_profile_redirect_me(self):
        loginUser(user_id='100')
        response = self.app.get('/profile/me')
        self.assertEqual(302, response.status_code)
        self.assertIn("<title>Redirecting...</title>", response.data)
        self.assertEqual("http://localhost/profile/BillGates", response.headers['Location'])

    def test_profile_user_does_not_exist(self):
        loginUser(user_id='200')
        response = self.app.get('/profile/1234')
        self.assertEqual(404, response.status_code)
        self.assertIn("User 1234 does not exist",
                      response.data,
                      msg="Missing message saying user doesn't exist")

    def test_new_user_postlogin(self):
        loginUser(user_id='404')
        response = self.app.get('/postlogin')
        self.assertEqual(302, response.status_code)
        self.assertIn("<title>Redirecting...</title>", response.data)
        self.assertEqual("http://localhost/signup?next=%2F", response.headers['Location'])

    def test_user_login_redirect(self):
        loginUser(user_id='100')
        next_url = urllib.urlencode({'next': "/profile/100"})
        response = self.app.get('/postlogin?' + next_url)
        self.assertEqual(302, response.status_code)
        self.assertIn("<title>Redirecting...</title>", response.data)
        self.assertEqual("http://localhost/profile/100", response.headers['Location'])

    def test_404_page(self):
        response = self.app.get('/page-that-isnt-there')
        self.assertEqual(404, response.status_code)
        self.assertIn("<h3>Page Not Found</h3>", response.data)


# TODO think of a scheme for testing permissions like the following.
# The dictionary is keeyed by the endpoint and for each endpoint there
# is a list of methods to run and a list of data to use for each method.
# Then there is an expected response code? (Just an idea to follow DRY)
#endpoints = {'/api/users/101': [('101', '201'), ]}


class UsersAPITestCase(unittest.TestCase):

    def setUp(self):
        # Used to debug 500 errors
        main.app.config['TESTING'] = True
        self.app = main.app.test_client()

    def test_get_user_list_as_officer(self):
        self.maxDiff = None
        loginUser(user_id="200")
        response = self.app.get('/api/users')
        self.assertEqual(200, response.status_code)
        expected = {
            u"users": [
                {
                    u'active': True,
                    u'classification': u"senior",
                    u'fname': u"Bill",
                    u'grad_semester': u"fall",
                    u'grad_year': 2015,
                    u'lname': u"Gates",
                    u'permissions': ["user"],
                    u'user_id': u"100",
                },
                {
                    u"active": True,
                    u"classification": u"senior",
                    u"fname": u"Jake",
                    u"grad_semester": u"fall",
                    u"grad_year": 2015,
                    u"lname": u"Sisko",
                    u'permissions': ["user"],
                    u"user_id": u"101",
                },
                {
                    u"active": False,
                    u"classification": u"freshman",
                    u"fname": u"Bob",
                    u"grad_semester": u"spring",
                    u"grad_year": 2016,
                    u"lname": u"Joe",
                    u'permissions': ["user", "officer"],
                    u"user_id": u"200",
                },
            ]
        }

        json_data = json.loads(response.data)
        self.assertIn('users', json_data)
        self.assertEqual(len(json_data['users']), 3)
        for u in json_data['users']:
            self.assertIn(u, expected['users'])

    def test_get_user_list_forbidden_not_logged_in(self):
        loginUser('', '')
        response = self.app.get('/api/users')
        self.assertEqual(403, response.status_code)
        data = json.loads(response.data)
        self.assertEqual("Not logged in", data['message'])

    def test_get_user_list_forbidden_not_officer(self):
        loginUser(user_id="100")
        response = self.app.get('/api/users')
        self.assertEqual(403, response.status_code)
        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])
        self.assertEqual(['officer'], data['perms'])

    def test_post_user_list(self):
        loginUser(user_id="300")
        post_data = {
            u'fname': u"James",
            u'lname': u"Kirk",
            u'classification': u"senior",
            u'grad_year': 2016,
            u'grad_semester': u"spring",
        }
        response = self.app.post("/api/users", data=post_data)
        self.assertEqual(201, response.status_code)

        # Get the returned location and check that it is the same
        # (plus a few extra fields)
        response = self.app.get(response.headers['location'])
        response_data = json.loads(response.data)
        post_data['active'] = True
        post_data['user_id'] = "300"
        post_data['point_exceptions'] = []
        post_data['permissions'] = ['user']
        self.assertEqual(post_data, response_data)

    def test_post_user_list_bad_classification(self):
        main.app.config['TESTING'] = False
        loginUser(user_id="300")
        post_data = {
            "fname": "James",
            "lname": "Kirk",
            "classification": "superman",
            "grad_year": 2016,
            "grad_semester": "spring",
        }
        response = self.app.post("/api/users", data=post_data)
        self.assertEqual(500, response.status_code)

    def test_post_user_list_empty_first_name(self):
        main.app.config['TESTING'] = False
        loginUser(user_id="300")
        post_data = {
            "fname": "",
            "lname": "Kirk",
            "classification": "senior",
            "grad_year": 2016,
            "grad_semester": "spring",
        }
        response = self.app.post("/api/users", data=post_data)
        self.assertEqual(500, response.status_code)

    def test_post_user_list_empty_last_name(self):
        main.app.config['TESTING'] = False
        loginUser(user_id="300")
        post_data = {
            "fname": "James",
            "lname": "",
            "classification": "senior",
            "grad_year": 2016,
            "grad_semester": "spring",
        }
        response = self.app.post("/api/users", data=post_data)
        self.assertEqual(500, response.status_code)

    def test_post_user_list_string_year(self):
        main.app.config['TESTING'] = False
        loginUser(user_id="300")
        post_data = {
            "fname": "James",
            "lname": "Kirk",
            "classification": "superman",
            "grad_year": "2016",
            "grad_semester": "spring",
        }
        response = self.app.post("/api/users", data=post_data)
        self.assertEqual(500, response.status_code)

    def test_post_user_list_bad_semester(self):
        main.app.config['TESTING'] = False
        loginUser(user_id="300")
        post_data = {
            "fname": "James",
            "lname": "Kirk",
            "classification": "senior",
            "grad_year": 2016,
            "grad_semester": "not_a_semester",
        }
        response = self.app.post("/api/users", data=post_data)
        self.assertEqual(500, response.status_code)

    def test_post_user_list_not_logged_in(self):
        main.app.config['TESTING'] = False
        post_data = {
            "fname": "James",
            "lname": "Kirk",
            "classification": "senior",
            "grad_year": 2016,
            "grad_semester": "spring",
        }
        response = self.app.post("/api/users", data=post_data)
        self.assertEqual(500, response.status_code)

    def test_post_user_list_duplicate_username(self):
        main.app.config['TESTING'] = False
        loginUser(user_id="300")
        post_data = {
            u'fname': u"Bill",
            u'lname': u"Gates",
            u'classification': u"senior",
            u'grad_year': 2016,
            u'grad_semester': u"spring",
        }
        response = self.app.post("/api/users", data=post_data)
        self.assertEqual(500, response.status_code)

    def test_get_own_user(self):
        loginUser(user_id="100")
        response = self.app.get('/api/users/100')
        self.assertEqual(200, response.status_code)
        data = json.loads(response.data)
        expected = {
            u'active': True,
            u'classification': u"senior",
            u'fname': u"Bill",
            u'grad_semester': u"fall",
            u'grad_year': 2015,
            u'lname': u"Gates",
            u'point_exceptions': [
                {
                    u'point_category': u"Mixers",
                    u'points_needed': 5
                }
            ],
            u'permissions': ['user'],
            u'user_id': u"100",
        }
        self.assertEqual(expected, data)

    def test_get_other_user_fails(self):
        loginUser(user_id="100")
        response = self.app.get('/api/users/200')
        self.assertEqual(403, response.status_code)
        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_get_other_user_as_officer(self):
        loginUser(user_id="200")
        response = self.app.get('/api/users/100')
        self.assertEqual(200, response.status_code)
        data = json.loads(response.data)
        expected = {
            u'active': True,
            u'classification': u"senior",
            u'fname': u"Bill",
            u'grad_semester': u"fall",
            u'grad_year': 2015,
            u'lname': u"Gates",
            u'point_exceptions': [
                {
                    u'point_category': u"Mixers",
                    u'points_needed': 5
                }
            ],
            u'permissions': ["user"],
            u'user_id': u"100",
        }
        self.assertEqual(expected, data)

    def test_put_current_user(self):
        loginUser(user_id="100")
        put_data = {
            u'fname': u"James",
            u'lname': u"Kirk",
            u'active': u"false",
            u'classification': u"junior",
            u'grad_year': 2016,
            u'grad_semester': u"spring",
        }
        response = self.app.put("/api/users/100", data=put_data)
        self.assertEqual(204, response.status_code)

        # Get the returned location and check that it is the same
        # (plus a few extra fields)
        response = self.app.get(response.headers['location'])
        response_data = json.loads(response.data)
        put_data[u'active'] = False
        put_data[u'user_id'] = "100"
        put_data[u'point_exceptions'] = [
            {
                u'point_category': u"Mixers",
                u'points_needed': 5
            }
        ]
        put_data[u'permissions'] = [u'user']
        self.assertEqual(put_data, response_data)

    def test_put_other_user_as_officer(self):
        loginUser(user_id="200")
        put_data = {
            u'fname': u"James",
            u'lname': u"Kirk",
            u'active': u"false",
            u'classification': u"junior",
            u'grad_year': 2016,
            u'grad_semester': u"spring",
        }
        response = self.app.put("/api/users/100", data=put_data)
        self.assertEqual(204, response.status_code)

        # Get the returned location and check that it is the same
        # (plus a few extra fields)
        response = self.app.get(response.headers['location'])
        response_data = json.loads(response.data)
        put_data[u'active'] = False
        put_data[u'user_id'] = u"100"
        put_data[u'point_exceptions'] = [
            {
                u'point_category': u"Mixers",
                u'points_needed': 5
            }
        ]
        put_data[u'permissions'] = ['user']
        self.assertEqual(put_data, response_data)

    def test_put_other_user_without_officer(self):
        loginUser(user_id="101")
        put_data = {
            'fname': "James",
            'lname': "Kirk",
            'active': "false",
            'classification': "junior",
            'grad_year': 2016,
            'grad_semester': "spring",
        }
        response = self.app.put("/api/users/100", data=put_data)
        self.assertEqual(403, response.status_code)

    def test_put_user_not_logged_in(self):
        put_data = {
            "fname": "James",
            "lname": "Kirk",
            "is_active": "true",
            "classification": "senior",
            "grad_year": 2016,
            "grad_semester": "spring",
        }
        response = self.app.put("/api/users/100", data=put_data)
        self.assertEqual(403, response.status_code)


class PointExceptionsAPITestCase(unittest.TestCase):

    def setUp(self):
        # Used to debug 500 errors
        main.app.config['TESTING'] = True
        self.app = main.app.test_client()
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_datastore_v3_stub()
        #ndb.get_context().clear_cache()
        setup_datastore()
        #pylint: disable=maybe-no-member

    def tearDown(self):
        self.testbed.deactivate()

    # TODO this code is duplicated in all api tests
    def loginUser(self, email='user@example.com', user_id='123', is_admin=False):
        self.testbed.setup_env(
            user_email=email,
            user_id=user_id,
            user_is_admin='1' if is_admin else '0',
            overwrite=True)

    def test_get_current_user_point_exception(self):
        self.loginUser(user_id="100")
        response = self.app.get('/api/users/100/point-exceptions/0')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            'point_category': "Mixers",
            'points_needed': 5,
        }
        self.assertEqual(expected, data)

    def test_get_other_user_point_exception_without_officer(self):
        self.loginUser(user_id="100")
        response = self.app.get('/api/users/200/point-exceptions/0')
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_get_other_user_point_exception_as_officer(self):
        self.loginUser(user_id="200")
        response = self.app.get('/api/users/100/point-exceptions/0')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            'point_category': "Mixers",
            'points_needed': 5,
        }
        self.assertEqual(expected, data)

    def test_get_user_point_exception_index_error(self):
        self.loginUser(user_id="200")
        response = self.app.get('/api/users/100/point-exceptions/1')
        self.assertEqual(response.status_code, 404)

        data = json.loads(response.data)
        self.assertEqual("Resource does not exist", data['message'])

    def test_delete_own_point_exception(self):
        self.loginUser(user_id="100")
        response = self.app.delete('/api/users/100/point-exceptions/0')
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

        # Officers shouldn't be able to delete their own excpeptions
        self.loginUser(user_id="200")
        response = self.app.delete('/api/users/200/point-exceptions/0')
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_delete_other_user_point_exception_without_officer(self):
        self.loginUser(user_id="100")
        response = self.app.delete('/api/users/200/point-exceptions/0')
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_delete_other_user_point_exception_as_officer(self):
        self.loginUser(user_id="200")
        response = self.app.delete('/api/users/100/point-exceptions/0')
        self.assertEqual(response.status_code, 200)

        response = self.app.get('/api/users/100')
        data = json.loads(response.data)
        self.assertEqual(data['point_exceptions'], [])

    def test_delete_non_existent_point_exception(self):
        self.loginUser(user_id="200")
        response = self.app.delete('/api/users/100/point-exceptions/1')
        self.assertEqual(response.status_code, 404)

    def test_get_own_point_exceptions(self):
        self.loginUser(user_id="100")
        response = self.app.get('/api/users/100/point-exceptions')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'point_exceptions': [
                {
                    u'point_category': u"Mixers",
                    u'points_needed': 5,
                },
            ]
        }
        self.assertEqual(data, expected)

    def test_get_other_user_point_exceptions_as_officer(self):
        self.loginUser(user_id="200")
        response = self.app.get('/api/users/100/point-exceptions')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'point_exceptions': [
                {
                    u'point_category': u"Mixers",
                    u'points_needed': 5,
                }
            ]
        }
        self.assertEqual(expected, data)

    def test_get_other_user_point_exceptions_without_officer(self):
        self.loginUser(user_id="100")
        response = self.app.get('/api/users/200/point-exceptions')
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_post_own_point_exception(self):
        self.loginUser(user_id="100")
        post_data = {
            u'point_category': u"philanthropy",
            u'points_needed': 10,
        }
        response = self.app.post("/api/users/100/point-exceptions", data=post_data)
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

        # Officer's can't change their own point exceptions
        self.loginUser(user_id="200")
        response = self.app.post("/api/users/200/point-exceptions", data=post_data)
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_post_other_user_point_exception_without_officer(self):
        self.loginUser(user_id="100")
        post_data = {
            u'point_category': u"philanthropy",
            u'points_needed': 10,
        }
        response = self.app.post("/api/users/200/point-exceptions", data=post_data)
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_post_other_user_point_exception_as_officer(self):
        self.loginUser(user_id="200")
        post_data = {
            u'point_category': u"philanthropy",
            u'points_needed': 10,
        }
        response = self.app.post("/api/users/100/point-exceptions", data=post_data)
        self.assertEqual(response.status_code, 201)

        response = self.app.get(response.headers['location'])
        response_data = json.loads(response.data)
        self.assertEqual(post_data, response_data)

    def test_post_existing_point_category_exception(self):
        self.loginUser(user_id="200")
        post_data = {
            u'point_category': u"philanthropy",
            u'points_needed': 10,
        }
        response = self.app.post("/api/users/100/point-exceptions", data=post_data)
        post_data['point_category'] = u"Mixers"
        response = self.app.post("/api/users/100/point-exceptions", data=post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'],
                         "http://localhost/api/users/100/point-exceptions/0")

        response = self.app.get("/api/users/100/point-exceptions/0")
        response_data = json.loads(response.data)
        self.assertEqual(post_data, response_data)


class PermissionsAPITestCase(unittest.TestCase):

    def setUp(self):
        # Used to debug 500 errors
        main.app.config['TESTING'] = True
        self.app = main.app.test_client()
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_datastore_v3_stub()
        #ndb.get_context().clear_cache()
        setup_datastore()
        #pylint: disable=maybe-no-member

    def tearDown(self):
        self.testbed.deactivate()

    # TODO this code is duplicated in all api tests
    def loginUser(self, email='user@example.com', user_id='123', is_admin=False):
        self.testbed.setup_env(
            user_email=email,
            user_id=user_id,
            user_is_admin='1' if is_admin else '0',
            overwrite=True)

    def test_get_permissions_as_officer(self):
        self.loginUser(user_id="200")
        response = self.app.get('/api/users/100/permissions')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'permissions': [u"user"],
        }
        self.assertEqual(expected, data)

        response = self.app.get('/api/users/200/permissions')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'permissions': [u"user", u"officer"],
        }
        self.assertEqual(expected, data)

    def test_get_permissions_as_user(self):
        self.loginUser(user_id="100")
        response = self.app.get('/api/users/100/permissions')
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_post_permissions_as_officer(self):
        self.loginUser(user_id="200")
        post_data = {
            u'permission': u"newperm",
        }
        response = self.app.post("/api/users/100/permissions", data=post_data)
        self.assertEqual(response.status_code, 201)

        self.assertEqual(response.headers['location'],
                         "http://localhost/api/users/100/permissions/newperm")

        response = self.app.get("/api/users/100/permissions")
        response_data = json.loads(response.data)
        expected = {
            u'permissions': [u"user", u"newperm"]
        }
        self.assertEqual(expected, response_data)

    def test_post_permissions_as_user(self):
        self.loginUser(user_id="100")
        post_data = {
            u'permission': u"newperm",
        }
        response = self.app.post("/api/users/100/permissions", data=post_data)
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_post_duplicate_permission(self):
        self.loginUser(user_id="200")
        post_data = {
            u'permission': u"user",
        }
        response = self.app.post("/api/users/100/permissions", data=post_data)
        self.assertEqual(response.status_code, 201)

        self.assertEqual(response.headers['location'],
                         "http://localhost/api/users/100/permissions/user")

        response = self.app.get("/api/users/100/permissions")
        response_data = json.loads(response.data)
        expected = {
            u'permissions': [u"user"]
        }
        self.assertEqual(expected, response_data)

    def test_delete_permission(self):
        self.loginUser(user_id="200")
        response = self.app.delete("/api/users/100/permissions/user")
        self.assertEqual(response.status_code, 200)

        response = self.app.get("/api/users/100/permissions")
        response_data = json.loads(response.data)
        expected = {
            u'permissions': [],
        }
        self.assertEqual(expected, response_data)

    def test_delete_non_existent_permission(self):
        self.loginUser(user_id="200")
        response = self.app.delete("/api/users/100/permissions/nonexistent_perm")
        self.assertEqual(response.status_code, 404)

        response = self.app.get("/api/users/100/permissions")
        response_data = json.loads(response.data)
        expected = {
            u'permissions': [u"user"],
        }
        self.assertEqual(expected, response_data)


class PointCategoriesAPITestCase(unittest.TestCase):

    def setUp(self):
        # Used to debug 500 errors
        main.app.config['TESTING'] = True
        self.app = main.app.test_client()
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_datastore_v3_stub()
        #ndb.get_context().clear_cache()
        setup_datastore()
        #pylint: disable=maybe-no-member

    def tearDown(self):
        self.testbed.deactivate()

    def loginUser(self, email='user@example.com', user_id='123', is_admin=False):
        self.testbed.setup_env(
            user_email=email,
            user_id=user_id,
            user_is_admin='1' if is_admin else '0',
            overwrite=True)

    def test_get_point_category_list_as_officer(self):
        self.loginUser(user_id="200")
        response = self.app.get('/api/point-categories')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'Sisterhood': {
                u'name': u'Sisterhood',
                u'baby_requirement': None,
                u'member_requirement': 20,
                u'sub_categories': [
                    {
                        u'name': u'Bloob Time',
                        u'baby_requirement': None,
                        u'member_requirement': 10,
                    },
                    {
                        u'name': u'Mixers',
                        u'baby_requirement': None,
                        u'member_requirement': 8,
                    }
                ]
            },

            u'Philanthropy': {
                u'name': u'Philanthropy',
                u'baby_requirement': None,
                u'member_requirement': 12,
                u'sub_categories': [],
            }
        }
        self.assertEqual(expected, data)

    def test_get_point_category_list_as_user(self):
        self.loginUser(user_id="100")
        response = self.app.get('/api/point-categories')
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_post_point_category_as_officer(self):
        self.loginUser(user_id="200")
        post_data = {
            u'name': u"Academics",
            u'parent': None,
        }
        response = self.app.post("/api/point-categories", data=post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'],
                         "http://localhost/api/point-categories/Academics")

        response = self.app.get("/api/point-categories")
        response_data = json.loads(response.data)
        expected = {
            u'name': u'Academics',
            u'baby_requirement': None,
            u'member_requirement': None,
            u'sub_categories': [],
        }
        self.assertEqual(expected, response_data['Academics'])

    def test_post_point_category_with_parent(self):
        self.loginUser(user_id="200")
        post_data = {
            u'name': u"Academics",
            u'parent': u"Philanthropy",
        }
        response = self.app.post("/api/point-categories", data=post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'],
                         "http://localhost/api/point-categories/Academics")

        response = self.app.get("/api/point-categories")
        response_data = json.loads(response.data)
        expected = {
            u'name': u'Academics',
            u'baby_requirement': None,
            u'member_requirement': None,
        }
        self.assertIn(expected, response_data['Philanthropy']['sub_categories'])

    def test_post_point_category_as_user(self):
        self.loginUser(user_id="100")
        post_data = {
            u'name': u"Academics",
            u'parent': u"Philanthropy",
        }
        response = self.app.post("/api/point-categories", data=post_data)
        self.assertEqual(response.status_code, 403)

    def test_post_duplicate_point_category(self):
        self.loginUser(user_id="200")
        post_data = {
            u'name': u"Philanthropy",
            u'parent': None,
        }
        response = self.app.post("/api/point-categories", data=post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'],
                         "http://localhost/api/point-categories/Philanthropy")

        response = self.app.get("/api/point-categories")
        response_data = json.loads(response.data)
        expected = {
            u'name': u'Philanthropy',
            u'baby_requirement': None,
            u'member_requirement': 12,
            u'sub_categories': [],
        }
        self.assertEqual(expected, response_data['Philanthropy'])

    def test_post_duplicate_point_sub_category(self):
        self.loginUser(user_id="200")
        post_data = {
            u'name': u"Bloob Time",
            u'parent': None,
        }
        response = self.app.post("/api/point-categories", data=post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'],
                         "http://localhost/api/point-categories/BloobTime")

        response = self.app.get("/api/point-categories")
        response_data = json.loads(response.data)
        expected = {
            u'baby_requirement': None,
            u'member_requirement': 10,
            u'name': u'Bloob Time',
            u'sub_categories': [],
        }
        self.assertEqual(expected, response_data['Bloob Time'])
        self.assertNotIn("Bloob Time", response_data['Sisterhood']['sub_categories'])

    def test_get_point_category(self):
        response = self.app.get("/api/point-categories/Sisterhood")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'name': u"Sisterhood",
            u'sub_categories': [u"Bloob Time", u"Mixers"],
        }
        self.assertEqual(expected, data)

    # TODO
    #def test_get_point_category_with_spaces(self):
    #def test_post_duplicate_point_category_with_diff_spaces(self):
    #def test_delete_point_category_as_officer(self):
    #def test_delete_point_category_as_user(self):
    #def test_delete_point_category_with_spaces(self):


class EventAPITestCase(unittest.TestCase):

    def setUp(self):
        # Used to debug 500 errors
        main.app.config['TESTING'] = True
        self.app = main.app.test_client()
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_datastore_v3_stub()
        #ndb.get_context().clear_cache()
        setup_datastore()
        #pylint: disable=maybe-no-member

    def tearDown(self):
        self.testbed.deactivate()

    def loginUser(self, email='user@example.com', user_id='123', is_admin=False):
        self.testbed.setup_env(
            user_email=email,
            user_id=user_id,
            user_is_admin='1' if is_admin else '0',
            overwrite=True)

    def test_get_all_events(self):
        self.loginUser(user_id="100")
        response = self.app.get('/api/events')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'events': [
                {
                    u'date': u"03/04/2016",
                    u'point-category': u"Philanthropy",
                    u'name': u"Habitat for Humanity",
                },
                {
                    u'date': u"05/03/2016",
                    u'point-category': u"Mixers",
                    u'name': u"Mixers Event",
                },
                {
                    u'date': u"08/02/2016",
                    u'point-category': u"Sisterhood",
                    u'name': u"Sisterhood Event",
                },
                {
                    u'date': u"08/03/2016",
                    u'point-category': u"Philanthropy",
                    u'name': u"My First Event",
                },
                {
                    u'date': u"09/01/2016",
                    u'point-category': u"Bloob Time",
                    u'name': u"Bloob Time Event",
                },
            ]
        }
        self.assertEqual(expected, data)

    def test_get_root_and_child_category_events(self):
        self.loginUser(user_id="100")
        response = self.app.get("/api/events?category=Sisterhood")
        #self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'events': [
                {
                    u'date': u'05/03/2016',
                    u'name': u'Mixers Event',
                    u'point-category': u'Mixers',
                },
                {
                    u'date': u"08/02/2016",
                    u'point-category': u"Sisterhood",
                    u'name': u"Sisterhood Event",
                },
                {
                    u'date': u"09/01/2016",
                    u'point-category': u"Bloob Time",
                    u'name': u"Bloob Time Event",
                },
            ]
        }
        self.assertEqual(expected, data)

    def test_get_child_events(self):
        self.loginUser(user_id="100")
        response = self.app.get("/api/events?category=Bloob%20Time")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'events': [
                {
                    u'date': u"09/01/2016",
                    u'point-category': u"Bloob Time",
                    u'name': u"Bloob Time Event",
                },
            ]
        }
        self.assertEqual(expected, data)

    def test_get_single_event_by_name(self):
        self.loginUser(user_id="100")
        response = self.app.get("/api/events/Bloob%20Time%20Event")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'date': u"09/01/2016",
            u'point-category': u"Bloob Time",
            u'name': u"Bloob Time Event",
        }
        self.assertEqual(expected, data)

    def test_get_single_event_without_spaces(self):
        self.loginUser(user_id="100")
        response = self.app.get("/api/events/BloobTimeEvent")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'date': u"09/01/2016",
            u'point-category': u"Bloob Time",
            u'name': u"Bloob Time Event",
        }
        self.assertEqual(expected, data)

    def test_get_nonexistent_event(self):
        self.loginUser(user_id="100")
        response = self.app.get("/api/events/ANonExistentEvent")
        self.assertEqual(response.status_code, 404)

    def test_post_event_as_user(self):
        self.loginUser(user_id="100")
        post_data = {
            u'name': u"Fall Ball 2016",
            u'date': u"2016-08-13",
            u'point-category': u"Philanthropy",
        }
        response = self.app.post("/api/events", data=post_data)
        self.assertEqual(response.status_code, 403)

    def test_post_event_as_officer(self):
        self.loginUser(user_id="200")
        post_data = {
            u'name': u"Spring Fling 2016",
            u'date': u"2016-03-01",
            u'point-category': "Bloob Time",
        }
        response = self.app.post("/api/events", data=post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'],
                         "http://localhost/api/events/SpringFling2016")

        response = self.app.get("/api/events")
        response_data = json.loads(response.data)
        expected = {
            u'date': u'03/01/2016',
            u'name': u'Spring Fling 2016',
            u'point-category': u'Bloob Time'
        }
        self.assertIn(expected, response_data['events'])

    def test_post_event_duplicate_name(self):
        self.loginUser(user_id="200")
        post_data = {
            u'name': u"Sisterhood Event",
            u'date': u"2016-03-01",
            u'point-category': "Bloob Time",
        }
        response = self.app.post("/api/events", data=post_data)
        self.assertEqual(response.status_code, 409)

    def test_post_event_bad_date(self):
        main.app.config['TESTING'] = False
        self.loginUser(user_id="200")
        post_data = {
            u'name': u"Fun Event",
            u'date': u"2016-30-01",
            u'point-category': "Bloob Time",
        }
        response = self.app.post("/api/events", data=post_data)
        self.assertEqual(response.status_code, 500)

    def test_delete_event_as_user(self):
        self.loginUser(user_id="100")
        response = self.app.delete("/api/events/BloobTimeEvent")
        self.assertEqual(response.status_code, 403)

    def test_delete_event_as_officer(self):
        self.loginUser(user_id="200")
        response = self.app.delete("/api/events/BloobTimeEvent")
        self.assertEqual(response.status_code, 200)

        response = self.app.get("/api/events")
        response_data = json.loads(response.data)
        expected = {
            u'events': [
                {
                    u'date': u"03/04/2016",
                    u'name': u"Habitat for Humanity",
                    u'point-category': u"Philanthropy",
                },
                {
                    u'date': u"05/03/2016",
                    u'name': u"Mixers Event",
                    u'point-category': u"Mixers",
                },
                {
                    u'date': u"08/02/2016",
                    u'name': u"Sisterhood Event",
                    u'point-category': u"Sisterhood",
                },
                {
                    u'date': u"08/03/2016",
                    u'name': u"My First Event",
                    u'point-category': u"Philanthropy",
                },
            ]
        }
        self.assertEqual(expected, response_data)

    def test_delete_non_existent_event(self):
        self.loginUser(user_id="200")
        response = self.app.delete("/api/events/NonExistentEvent")
        self.assertEqual(response.status_code, 404)


class PointRecordAPITestCase(unittest.TestCase):

    def setUp(self):
        # Used to debug 500 errors
        main.app.config['TESTING'] = True
        self.app = main.app.test_client()
        #pylint: disable=maybe-no-member

    def test_put_nonexistent_point_record(self):
        loginUser(user_id="200")
        put_data = {
            u'username': u"BillGates",
            u'event_name': u"Bloob Time Event",
            u'points-earned': 2,
        }
        response = self.app.put("/api/point-records", data=put_data)
        self.assertEqual(204, response.status_code)

        response = self.app.get("/api/point-records")
        response_data = json.loads(response.data)
        expected = {
            u'event_name': "Bloob Time Event",
            u'point-category': u'Bloob Time',
            u'username': 'BillGates',
            u'points-earned': 2.0,
        }
        self.assertIn(expected, response_data['records'])

    def test_put_existing_point_record(self):
        loginUser(user_id="200")
        put_data = {
            u'username': u"BillGates",
            u'event_name': u"Bloob Time Event",
            u'points-earned': 2.0,
        }
        response = self.app.put("/api/point-records", data=put_data)
        self.assertEqual(204, response.status_code)

        put_data = {
            u'username': u"BillGates",
            u'event_name': u"Bloob Time Event",
            u'points-earned': 4.0,
        }
        response = self.app.put("/api/point-records", data=put_data)
        self.assertEqual(204, response.status_code)

        response = self.app.get("/api/point-records")
        response_data = json.loads(response.data)
        expected = {
            u'event_name': "Bloob Time Event",
            u'point-category': u'Bloob Time',
            u'username': 'BillGates',
            u'points-earned': 4.0,
        }
        self.assertIn(expected, response_data['records'])


class UserPointsAPITestCase(unittest.TestCase):

    def setUp(self):
        self.app = main.app.test_client()

    def test_get_points_with_exception(self):
        loginUser(user_id="100")
        response = self.app.get('/api/users/100/points')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'required': 5,
            u'received': 2,
            u'level': 2
        }
        self.assertEqual(expected, data['Sisterhood']['sub_categories']['Mixers'])

    def test_get_points_with_parent_category(self):
        loginUser(user_id="101")
        response = self.app.get('/api/users/101/points')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected_sisterhood = {
            u'required': 20,
            u'received': 4,
            u'level': 1,
            u'sub_categories': {
                "Mixers": {
                    "received": 0,
                    "required": 8,
                    "level": 2
                },
                u'Bloob Time': {
                    u'required': 10,
                    u'received': 3,
                    u'level': 2,
                }
            }
        }
        self.assertEqual(expected_sisterhood, data['Sisterhood'])

    def test_get_points_with_multiple_records(self):
        loginUser(user_id="200")
        response = self.app.get('/api/users/200/points')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        expected = {
            u'required': 12,
            u'received': 3,
            u'level': 1,
            u'sub_categories': {},
        }
        self.assertEqual(expected, data['Philanthropy'])

    # TODO:
    #def test_get_other_user_points_as_user(self):
    #def test_get_other_user_points_as_officer(self):


if __name__ == '__main__':
    setup_testbed()
    unittest.main()
