import sys
import os
import unittest
import tempfile

def fix_sys_path():
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib', 'google_appengine'))

fix_sys_path()

from google.appengine.ext import testbed

import main

class MainTestCase(unittest.TestCase):

    def setUp(self):
        self.app = main.app.test_client()
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_return_idx(self):
        rv = self.app.get("/")
        assert "<h1> Index </h1>" in rv.data

if __name__ == '__main__':
    unittest.main()
