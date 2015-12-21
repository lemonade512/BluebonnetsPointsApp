import sys
import os
import unittest
import tempfile

from google.appengine.ext import testbed

import main
from models import UserData

class MainTestCase(unittest.TestCase):

    def setUp(self):
        self.app = main.app.test_client()
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_datastore_v3_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def loginUser(self, email='user@example.com', id='123', is_admin=False):
        self.testbed.setup_env(
            user_email=email,
            user_id=id,
            user_is_admin='1' if is_admin else '0',
            overwrite=True)

    def test_return_idx(self):
        rv = self.app.get("/")
        assert "<h1> Index </h1>" in rv.data

    def test_members_page_off_limits_to_user(self):
        u = UserData(id='111')
        u.user_permissions = ['user']
        u.user_id = '111'
        u.put()

        self.loginUser(id='111')
        response = self.app.get('/members')
        self.assertEqual(response.status_code, 403)
        s = "You need the following permissions to view that page: [&#39;officer&#39;]"
        self.assertIn(s, response.data)

    def test_members_page_available_to_officer(self):
        u = UserData(id='111')
        u.user_permissions = ['user', 'officer']
        u.user_id = '111'
        u.active = True
        u.first_name = "Bob"
        u.last_name = "Joe"
        u.put()

        self.loginUser(id='111')
        response = self.app.get('/members')
        self.assertEqual(response.status_code, 200)
        s = "Welcome to the members screen Bob Joe!"
        self.assertIn(s, response.data)

if __name__ == '__main__':
    unittest.main()
