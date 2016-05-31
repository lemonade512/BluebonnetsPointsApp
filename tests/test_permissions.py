import unittest
import urllib
import json
import mock

from google.appengine.ext import testbed
#from google.appengine.ext import ndb

import permissions
import pdb
import utils

class PermissionsTestCase(unittest.TestCase):

    @mock.patch('models.user_model.UserData.get_from_url_segment')
    @mock.patch('permissions.render_jinja_template')
    @mock.patch('models.user_model.UserData.get_current_user_data')
    def test_require_permissions_not_logged_in(self, mock_user, mock_jinja, mock_other_user):
        mock_user.return_value = None
        mock_other_user.return_value = None

        fn = mock.Mock(name="fn")
        fn.__name__ = 'fn'

        wrapped = permissions.require_permissions(['officer'])(fn)
        wrapped()
        self.assertEqual(fn.call_count, 0)
        mock_jinja.assert_called_with('nologin.html', {'message': 'Not logged in'})

    @mock.patch('models.user_model.UserData.get_from_url_segment')
    @mock.patch('permissions.render_jinja_template')
    @mock.patch('models.user_model.UserData.get_current_user_data')
    def test_require_permissions_not_officer(self, mock_user, mock_jinja, mock_other_user):
        class MockUser():
            user_permissions = []
        user = MockUser()
        user.user_permissions = ['user']
        mock_user.return_value = user
        mock_other_user.return_value = user

        fn = mock.Mock(name="fn")
        fn.__name__ = "fn"

        wrapped = permissions.require_permissions(['officer'])(fn)
        wrapped()
        self.assertEqual(fn.call_count, 0)
        mock_jinja.assert_called_with('nopermission.html',
                                      {'perms': ['officer'],
                                       'message': "Don't have permission"})

    @mock.patch('models.user_model.UserData.get_from_url_segment')
    @mock.patch('permissions.render_jinja_template')
    @mock.patch('models.user_model.UserData.get_current_user_data')
    def test_require_permissions_valid(self, mock_user, mock_jinja, mock_other_user):
        class MockUser():
            user_permissions = []
        user = MockUser()
        user.user_permissions = ['user', 'officer']
        mock_user.return_value = user
        mock_other_user.return_value = user

        fn = mock.Mock(name="fn")
        fn.__name__ = "fn"

        wrapped = permissions.require_permissions(['user', 'officer'])(fn)
        wrapped()
        self.assertEqual(fn.call_count, 1)

