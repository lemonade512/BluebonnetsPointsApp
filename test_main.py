import unittest
import urllib
import json
import mock

from google.appengine.ext import testbed
#from google.appengine.ext import ndb

import main
from models import UserData, PointException

#pylint: disable=too-many-public-methods
class MainTestCase(unittest.TestCase):

    @staticmethod
    def setup_datastore():
        u = UserData(id='100')
        u.user_permissions = ['user']
        u.user_id = '100'
        u.active = True
        u.first_name = "Bill"
        u.last_name = "Gates"
        u.put()

        u = UserData(id='200')
        u.user_permissions = ['user', 'officer']
        u.user_id = '200'
        u.active = True
        u.first_name = "Bob"
        u.last_name = "Joe"
        u.put()

    @classmethod
    def setUpClass(cls):
        cls.app = main.app.test_client()
        cls.testbed = testbed.Testbed()
        cls.testbed.activate()
        cls.testbed.init_user_stub()
        cls.testbed.init_memcache_stub()
        cls.testbed.init_datastore_v3_stub()
        #ndb.get_context().clear_cache()
        cls.setup_datastore()
        #pylint: disable=maybe-no-member

    @classmethod
    def tearDownClass(cls):
        cls.testbed.deactivate()

    def setUp(self):
        # Make sure no user is logged in
        self.loginUser('', '')

    def loginUser(self, email='user@example.com', user_id='123', is_admin=False):
        self.testbed.setup_env(
            user_email=email,
            user_id=user_id,
            user_is_admin='1' if is_admin else '0',
            overwrite=True)

    def test_logged_out_homepage(self):
        rv = self.app.get("/")
        self.assertEqual(200, rv.status_code)
        self.assertIn("Welcome to the main page!",
                      rv.data,
                      msg="Does not show proper welcome")

    @mock.patch('main.render_jinja_template')
    def test_logged_in_homepage(self, mock_jinja):
        mock_jinja.return_value = "Hello"
        self.loginUser(user_id='100')
        response = self.app.get("/")
        mock_jinja.assert_called_with('dashboard.html', {'active_page': 'home'})

    def test_members_page_off_limits_to_user(self):
        self.loginUser(user_id='100')
        response = self.app.get('/members')
        self.assertEqual(403, response.status_code)
        s = ("You need the following permissions to view that page:"
             " [&#39;officer&#39;]")
        self.assertIn(s, response.data, msg="Does not show necessary permissions")

    def test_members_page_available_to_officer(self):
        self.loginUser(user_id='200')
        response = self.app.get('/members')
        self.assertEqual(200, response.status_code)

    def test_admin_page_off_limits(self):
        self.loginUser(user_id='100', is_admin=False)
        response = self.app.get('/admin')
        self.assertEqual(403, response.status_code)
        s = ("You need the following permissions to view that page:"
             " [&#39;admin&#39;]")
        self.assertIn(s, response.data)

    def test_profile_redirect_to_username(self):
        self.loginUser(user_id='100')
        response = self.app.get('/profile/100')
        self.assertEqual(302, response.status_code)
        self.assertIn("<title>Redirecting...</title>", response.data)
        # TODO test a user with the same name being redirected to a different username
        self.assertEqual("http://localhost/profile/BillGates", response.headers['Location'])

    def test_profile_username_ok_status(self):
        self.loginUser(user_id="100")
        response = self.app.get('/profile/BillGates')
        self.assertEqual(200, response.status_code)

    def test_profile_redirect_me(self):
        self.loginUser(user_id='100')
        response = self.app.get('/profile/me')
        self.assertEqual(302, response.status_code)
        self.assertIn("<title>Redirecting...</title>", response.data)
        self.assertEqual("http://localhost/profile/BillGates", response.headers['Location'])

    def test_profile_user_does_not_exist(self):
        self.loginUser(user_id='200')
        response = self.app.get('/profile/1234')
        self.assertEqual(404, response.status_code)
        self.assertIn("User 1234 does not exist",
                      response.data,
                      msg="Missing message saying user doesn't exist")

    def test_new_user_postlogin(self):
        self.loginUser(user_id='404')
        response = self.app.get('/postlogin')
        self.assertEqual(302, response.status_code)
        self.assertIn("<title>Redirecting...</title>", response.data)
        self.assertEqual("http://localhost/signup?next=%2F", response.headers['Location'])

    def test_user_login_redirect(self):
        self.loginUser(user_id='100')
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

    @staticmethod
    def setup_datastore():
        u = UserData(id='100')
        u.user_permissions = ['user']
        u.user_id = '100'
        u.active = True
        u.first_name = "Bill"
        u.last_name = "Gates"
        u.classification = "senior"
        u.graduation_year = 2015
        u.graduation_semester = "fall"
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
        u.put()

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
        self.setup_datastore()
        #pylint: disable=maybe-no-member

    def tearDown(self):
        self.testbed.deactivate()

    def loginUser(self, email='user@example.com', user_id='123', is_admin=False):
        self.testbed.setup_env(
            user_email=email,
            user_id=user_id,
            user_is_admin='1' if is_admin else '0',
            overwrite=True)

    def test_get_user_list_as_officer(self):
        self.maxDiff = None
        self.loginUser(user_id="200")
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
        response = self.app.get('/api/users')
        self.assertEqual(403, response.status_code)
        data = json.loads(response.data)
        self.assertEqual("Not logged in", data['message'])

    def test_get_user_list_forbidden_not_officer(self):
        self.loginUser(user_id="100")
        response = self.app.get('/api/users')
        self.assertEqual(403, response.status_code)
        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])
        self.assertEqual(['officer'], data['perms'])

    def test_post_user_list(self):
        self.loginUser(user_id="300")
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
        self.loginUser(user_id="300")
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
        self.loginUser(user_id="300")
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
        self.loginUser(user_id="300")
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
        self.loginUser(user_id="300")
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
        self.loginUser(user_id="300")
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

    def test_get_own_user(self):
        self.loginUser(user_id="100")
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
            u'point_exceptions': [],
            u'permissions': ['user'],
            u'user_id': u"100",
        }
        self.assertEqual(expected, data)

    def test_get_other_user_fails(self):
        self.loginUser(user_id="100")
        response = self.app.get('/api/users/200')
        self.assertEqual(403, response.status_code)
        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_get_other_user_as_officer(self):
        self.loginUser(user_id="200")
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
            u'point_exceptions': [],
            u'permissions': ["user"],
            u'user_id': u"100",
        }
        self.assertEqual(expected, data)

    def test_put_current_user(self):
        self.loginUser(user_id="100")
        put_data = {
            'fname': "James",
            'lname': "Kirk",
            'active': "false",
            'classification': "junior",
            'grad_year': 2016,
            'grad_semester': "spring",
        }
        response = self.app.put("/api/users/100", data=put_data)
        self.assertEqual(204, response.status_code)

        # Get the returned location and check that it is the same
        # (plus a few extra fields)
        response = self.app.get(response.headers['location'])
        response_data = json.loads(response.data)
        put_data['active'] = False
        put_data['user_id'] = "100"
        put_data['point_exceptions'] = []
        put_data['permissions'] = ['user']
        self.assertEqual(put_data, response_data)

    def test_put_other_user_as_officer(self):
        self.loginUser(user_id="200")
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
        put_data[u'point_exceptions'] = []
        put_data[u'permissions'] = ['user']
        self.assertEqual(put_data, response_data)

    def test_put_other_user_without_officer(self):
        self.loginUser(user_id="101")
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

    @staticmethod
    def setup_datastore():
        meetings_exception = PointException()
        meetings_exception.point_type = "meetings"
        meetings_exception.points_needed = 5

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
            meetings_exception
        ]
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
            meetings_exception
        ]
        u.put()

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
        self.setup_datastore()
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
            'point_type': "meetings",
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
            'point_type': "meetings",
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
                    u'point_type': u"meetings",
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
                    u'point_type': u"meetings",
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
            u'point_type': u"philanthropy",
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
            u'point_type': u"philanthropy",
            u'points_needed': 10,
        }
        response = self.app.post("/api/users/200/point-exceptions", data=post_data)
        self.assertEqual(response.status_code, 403)

        data = json.loads(response.data)
        self.assertEqual("Don't have permission", data['message'])

    def test_post_other_user_point_exception_as_officer(self):
        self.loginUser(user_id="200")
        post_data = {
            u'point_type': u"philanthropy",
            u'points_needed': 10,
        }
        response = self.app.post("/api/users/100/point-exceptions", data=post_data)
        self.assertEqual(response.status_code, 201)

        response = self.app.get(response.headers['location'])
        response_data = json.loads(response.data)
        self.assertEqual(post_data, response_data)

    def test_post_existing_point_type_exception(self):
        self.loginUser(user_id="200")
        post_data = {
            u'point_type': u"philanthropy",
            u'points_needed': 10,
        }
        response = self.app.post("/api/users/100/point-exceptions", data=post_data)
        post_data['point_type'] = u"meetings"
        response = self.app.post("/api/users/100/point-exceptions", data=post_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['location'],
                         "http://localhost/api/users/100/point-exceptions/0")

        response = self.app.get("/api/users/100/point-exceptions/0")
        response_data = json.loads(response.data)
        self.assertEqual(post_data, response_data)


class PermissionsAPITestCase(unittest.TestCase):

    @staticmethod
    def setup_datastore():
        meetings_exception = PointException()
        meetings_exception.point_type = "meetings"
        meetings_exception.points_needed = 5

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
            meetings_exception
        ]
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
            meetings_exception
        ]
        u.put()

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
        self.setup_datastore()
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


if __name__ == '__main__':
    unittest.main()
