import unittest
import urllib

from google.appengine.ext import testbed
#from google.appengine.ext import ndb

import main
from models import UserData

#pylint: disable=too-many-public-methods
class MainTestCase(unittest.TestCase):

    @staticmethod
    def add_user_to_datastore():
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
        cls.add_user_to_datastore()
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

    def test_logged_in_homepage(self):
        self.loginUser(user_id='100')
        rv = self.app.get("/")
        self.assertEqual(200, rv.status_code)
        self.assertIn("Welcome to the main page Bill!",
                      rv.data,
                      msg="Does not show proper welcome")

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
        response = self.app.get('/profile/BillGates')
        self.assertEqual(200, response.status_code)

    def test_profile_redirect_me(self):
        self.loginUser(user_id='100')
        response = self.app.get('/profile/me')
        self.assertEqual(302, response.status_code)
        self.assertIn("<title>Redirecting...</title>", response.data)
        self.assertEqual("http://localhost/profile/BillGates", response.headers['Location'])

    def test_profile_user_does_not_exist(self):
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

if __name__ == '__main__':
    unittest.main()
