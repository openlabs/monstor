# -*- coding: utf-8 -*-
"""
    test_models

    Test by creating data in the models

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import requests 
import unittest2 as unittest
from mongoengine import connect, ValidationError, StringField
from mongoengine.connection import _get_connection

from monstor.contrib.auth.models import User

class TestModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        connect("test_auth")

    def setUp(self):
        new_user = User(
            name="Sharoon Thomas", 
            email="sharoon.thomas@openlabs.co.in",
            )
        new_user.set_password("openlabs")
        new_user.save()

    def tearDown(self):
        User.drop_collection()

    def test_0010_create_user(self):
        """
        Create a user
        """


        new_user = User(
            name="Sharoon Thomas", 
            email="sharoon.thomas@openlabs.co.in",
            )
        self.assertRaises(ValidationError, new_user.save)

        User.drop_collection()

    def test_0020_login(self):
        """
        Test the login
        """
        self.assertEqual(
            User.authenticate('something_user', 'some_password'), None
        )
        self.assertEqual(
            User.authenticate("sharoon.thomas@openlabs.co.in", "wrong"), False
        )
        self.assertEqual(
            User.authenticate("sharoon.thomas@openlabs.co.in", "openlabs"),
            User.objects(email="sharoon.thomas@openlabs.co.in").first()
        )

    def test_0030_gravatar(self):
        """
        Test the gravatar functionality
        """
        # Create an user with an email that will never exist
        sharoon = User.objects(email="sharoon.thomas@openlabs.co.in").first()
        self.assertTrue(sharoon.get_gravatar(size=50))
        self.assertTrue(sharoon.get_gravatar(default="some other url"))
        url = sharoon.get_gravatar()
        rv = requests.get(url)
        self.assertEqual(rv.status_code, 200)

    def test_0040_allow_inheritance(self):
        """
        The user model must allow inheritance
        """
        class AnExtendedUser(User):
            extended_field = StringField()
            meta = {
            }

        user = AnExtendedUser(name="Sharoon Thomas", email="email@example.com")
        user.save()
        self.assertEqual(User.objects().count(), 2)
        self.assertEqual(AnExtendedUser.objects().count(), 1)

    @classmethod
    def tearDownClass(cls):
        c = _get_connection()
        c.drop_database('test_auth')



if __name__ == '__main__':
    unittest.main()
