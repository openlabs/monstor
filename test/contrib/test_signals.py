# -*- coding: utf-8 -*-
"""
    test_signals

    Test the signals API

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import os
import unittest
from urllib import urlencode

import tornado
from tornado import testing, options
from monstor.app import make_app
from monstor.contrib.auth.models import User
from monstor.utils.web import BaseHandler
from mongoengine.connection import get_connection
from monstor.contrib.auth.signals import login_success, login_failure

COUNTER = {'success': 0, 'failure': 0}


@login_success.connect
def success_receiver(sender, **kw):
    """
    Signal receiver
    """
    COUNTER['success'] += 1


@login_failure.connect
def failure_receiver(sender):
    """
    Signal receiver
    """
    COUNTER['failure'] += 1


class DummyHomeHandler(BaseHandler):
    """
    A dummy homepage
    """
    def get(self):
        self.write("Welcome Home")


class urls(object):
    """
    Fool monstor into believeing that this is an app folder and load the
    HANDLER
    """
    HANDLERS = [
        tornado.web.URLSpec(r'/', DummyHomeHandler, name='home')
    ]


class TestSignals(testing.AsyncHTTPTestCase):

    def get_app(self):
        options.options.database = 'test_signal'
        settings = {
            'installed_apps': [
                'monstor.contrib.auth',
                __name__,
            ],
            'template_path': os.path.join(
                os.path.dirname(__file__), "templates"
            ),
            'login_url': '/login',
            'xsrf_cookies': False,
            'cookie_secret': 'nbgdhfjvgdfglkjdfkgjdfi',
        }
        application = make_app(**settings)
        return application

    def setUp(self):
        super(TestSignals, self).setUp()
        COUNTER['success'] = COUNTER['failure'] = 0

    def test_0010_login_post_1(self):
        """
        Test login with a user which already exists
        """
        user = User(name="Test User", email="test@example.com")
        user.set_password("password")
        user.save()
        response = self.fetch(
            '/login', method="POST", follow_redirects=False,
            body=urlencode({
                'email': 'test@example.com', 'password': 'password'
            })
        )
        self.assertEqual(COUNTER['success'], 1)
        self.assertEqual(COUNTER['failure'], 0)
        self.assertEqual(response.code, 302)

    def test_0020_login_post_2(self):
        """
        Test LoginHandler 'post' method
        Test login with a user which does not exist
        """
        response = self.fetch(
            '/login', method="POST", follow_redirects=False,
            body=urlencode({
                'email': 'test@example.com', 'password': 'password'
            })
        )
        self.assertEqual(COUNTER['failure'], 1)
        self.assertEqual(COUNTER['success'], 0)
        self.assertEqual(response.code, 200)

    def tearDown(self):
        """
        Drop the database after every test
        """
        get_connection().drop_database('test_signal')


if __name__ == '__main__':
    unittest.main()
