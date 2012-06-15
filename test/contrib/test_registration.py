# -*- coding: utf-8 -*-
"""
    test_organisations

    Test the organisations API

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import os
import unittest
import smtplib
from urllib import urlencode
from contextlib import nested

import tornado
from mock import patch
from tornado import testing, options
from monstor.app import make_app
from monstor.contrib.auth.models import User
from monstor.utils.web import BaseHandler
from mongoengine.connection import get_connection
from itsdangerous import URLSafeSerializer


class DummyHomeHandler(BaseHandler):
    """
    A dummy homepage
    """
    def get(self):
        self.write("Welcome Home")


class urls(object):
    """
    Fool monstor into believeing that this is an app folder and load the
    HANDLERS
    """
    HANDLERS = [
        tornado.web.URLSpec(r'/', DummyHomeHandler, name='home')
    ]


class TestRegistration(testing.AsyncHTTPTestCase):

    def get_app(self):

        options.options.database = 'test_monstor_registration'
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
            'cookie_secret': 'something-supposed-2-b-random',
        }
        application = make_app(**settings)
        return application

    def test_0010_login_get(self):
        """
        Test LoginHandler 'get' method
        """
        response = self.fetch('/login', method="GET", follow_redirects=False)
        self.assertEqual(response.code, 200)

    def test_0020_login_post_1(self):
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
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.body.count(u'The email or password is invalid'), 1
        )

    def test_0030_login_post_2(self):
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
        self.assertEqual(response.code, 302)

    def test_0040_registration_get(self):
        """
        Test RegistrationHandler 'get' method
        """
        response = self.fetch(
            '/registration', method="GET", follow_redirects=False
        )
        self.assertEqual(response.code, 200)

    def test_0050_registration_post_1(self):
        """
        Test RegistrationHandler 'post' method
        Test with wrong confirm password
        """
        response = self.fetch(
            '/registration', method="POST", follow_redirects=False,
            body=urlencode({'name':'anoop', 'email':'pqr@example.com',
                'password':'openlabs', 'confirm_password':'wrong'}
            )
        )
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.body.count(
                u'There were error(s) in processing your registration.'
            ), 1
        )

    def test_0060_registration_post_2(self):
        """
        Test registration with an user which already exists
        """
        user = User(name="Test User", email="test@example.com")
        user.set_password("password")
        user.save()
        response = self.fetch(
            '/registration', method="POST", follow_redirects=False,
            body=urlencode({'name':'anoop', 'email':'test@example.com',
                'password':'openlabs', 'confirm_password':'openlabs'}
            )
        )
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.body.count(u'This email is already registered.'), 1
        )

    def test_0070_registration_post_3(self):
        """
        Test registration with an email which already exists,
        with require_activation = True
        """
        options.options.require_activation = True
        user = User(name="Test User", email="test@example.com")
        user.set_password("password")
        user.save()
        with nested(
                patch.object(smtplib.SMTP, 'sendmail'),
                patch.object(smtplib.SMTP, 'quit'),
                ) as (mock_sendmail, mock_quit):
            response = self.fetch(
                '/registration', method="POST", follow_redirects=False,
                body=urlencode({'name':'anoop',
                    'email':'test@example.com',
                    'password':'openlabs', 'confirm_password':'openlabs'}
                )
            )
            self.assertEqual(mock_sendmail.call_count, 0)
            self.assertEqual(mock_quit.call_count, 0)
            self.assertEqual(response.code, 200)
            self.assertEqual(
                response.body.count(
                    u'This email is already registered.'
                ), 1
            )

    def test_0080_registration_post_4(self):
        """
        Test registration with a new user,
        with require_activation = True
        """
        options.options.require_activation = True
        with nested(
                patch.object(smtplib.SMTP, 'sendmail'),
                patch.object(smtplib.SMTP, 'quit'),
                ) as (mock_sendmail, mock_quit):
            response = self.fetch(
                '/registration', method="POST", follow_redirects=False,
                body=urlencode({'name':'anoop',
                    'email':'anoop.sm@openlabs.co.in',
                    'password':'openlabs', 'confirm_password':'openlabs'}
                )
            )
            self.assertEqual(mock_sendmail.call_count, 1)
            self.assertEqual(mock_quit.call_count, 1)
            self.assertEqual(response.code, 302)

    def test_0090_test_registration_post_5(self):
        """
        Test registration with a new user,
        with require_activation=False
        """
        options.options.require_activation = False
        with nested(
                patch.object(smtplib.SMTP, 'sendmail'),
                patch.object(smtplib.SMTP, 'quit'),
            ) as (mock_sendmail, mock_quit):
            response = self.fetch(
                '/registration', method="POST", follow_redirects=False,
                body=urlencode({'name':'anoop',
                    'email':'test@example.com',
                    'password':'openlabs', 'confirm_password':'openlabs'}
                )
            )
            self.assertEqual(mock_sendmail.call_count, 0)
            self.assertEqual(mock_quit.call_count, 0)
            self.assertEqual(response.code, 302)

    def test_0100_activationkey_resend_get(self):
        """
        Test ActivationkeyResendHandler 'get' method
        """
        response = self.fetch(
            '/activation_resend', method="GET", follow_redirects=False,
        )
        self.assertEqual(response.code, 200)

    def test_0110_activationkey_resend_post_1(self):
        """
        Test ActivationkeyresendHandler 'post' method
        Test resend with a user which does not exist
        """
        response = self.fetch(
            '/activation_resend', method="POST", follow_redirects=False,
            body=urlencode({'email':'abc@example.com'})
        )
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.body.count(u'we could not match your email'), 1
        )

    def test_0120_activationkey_resend_post_2(self):
        """
        Test resend with a user which already exists
        """
        user = User(name="Test User", email="test@example.com")
        user.set_password("password")
        user.save()
        with nested(
                patch.object(smtplib.SMTP, 'sendmail'),
                patch.object(smtplib.SMTP, 'quit'),
                ) as (mock_sendmail, mock_quit):
            response = self.fetch(
                '/activation_resend', method="POST", follow_redirects=False,
                body=urlencode({'email':'test@example.com'})
            )
        self.assertEqual(mock_sendmail.call_count, 1)
        self.assertEqual(mock_quit.call_count, 1)
        self.assertEqual(response.code, 302)

    def test_0130_account_activation_1(self):
        """
        Test activation of account with true activationkey
        """
        user = User(name="Test User", email="test@example.com")
        user.set_password("password")
        user.save()
        signer = URLSafeSerializer(self.get_app().settings['cookie_secret'])
        activation_key = signer.dumps(user.email)
        response = self.fetch(
            '/activation/%s' % activation_key,
            method="GET", follow_redirects=False,
        )
        self.assertEqual(response.code, 302)

    def test_0140_account_activation_2(self):
        """
        Test account activation with wrong activationkey
        """
        signer = URLSafeSerializer(self.get_app().settings['cookie_secret'])
        activation_key = signer.dumps("def@sample.com")
        response = self.fetch(
            '/activation/%s' % activation_key,
            method="GET", follow_redirects=False
        )
        self.assertEqual(response.code, 302)
        cookies = response.headers.get('Set-Cookie')
        response = self.fetch(
            '/registration', method="GET", headers={
                'Cookie': cookies
            }
        )
        self.assertEqual(
            response.body.count(u'Invalid Activation Key, Please register.'), 1
        )


    def tearDown(self):
        """
        Drop the database after every test
        """
        get_connection().drop_database('test_monstor_registration')


if __name__ == '__main__':
    unittest.main()
