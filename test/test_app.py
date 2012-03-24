# -*- coding: utf-8 -*-
"""
    test_app

    Test the application builder

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
import unittest2 as unittest

from monstor.app import make_app
from monstor.exc import InvalidRequestError


class TestMakeApp(unittest.TestCase):

    def test_0010_make_app_wo_db(self):
        """
        Build a simple app to test w/o DB
        """
        with self.assertRaises(InvalidRequestError):
            app = make_app(installed_apps=[
                'monstor.contrib.auth',
            ])

    def test_0020_make_app(self):
        """
        Build a simple app to test
        """
        from tornado.options import options
        options.database = 'test_db'
        app = make_app(installed_apps=[
            'monstor.contrib.auth',
        ])


if __name__ == "__main__":
    unittest.main()
