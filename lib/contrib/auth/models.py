# -*- coding: utf-8 -*-
"""
    models

    Models for User Authentication

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import urllib
import hashlib
import random
import string

import pytz
from mongoengine import Document, ValidationError
from mongoengine import StringField, EmailField, BooleanField
from monstor.utils.i18n import _


class User(Document):
    """
    User Object
    """
    company_name = StringField(verbose_name=_("Name"))
    name = StringField(required=True, verbose_name=_("Name"))
    active = BooleanField(default=False, verbose_name=_("Active"))
    suspended = BooleanField(default=False, verbose_name=_("Suspended"))

    #: This field has to be unique but mongoengine on sending unique as True
    #: sets the same on the index. MongoDB considers NULL also as a unique
    #: value and that ends up being trouble.
    #: 
    #: So this is manually implemented in :meth:validate
    email = EmailField(verbose_name=_("Email"))
    locale = StringField()
    timezone = StringField(
        choices=[(tz, tz) for tz in pytz.common_timezones], default='UTC'
    )

    # For old school logins
    # .. note::
    #   Do not set the value of salt or password directly instaed use the 
    #   methods :meth:`set_password` instead
    salt = StringField()
    password = StringField(verbose_name=_("Password"))

    # Federated login data

    # Facebook
    facebook_id = StringField()
    facebook_picture = StringField()
    facebook_username = StringField()
    facebook_link = StringField()

    # Google
    # Google we could reuse the email itself

    # Twitter
    twitter_id = StringField()
    twitter_description = StringField()
    twitter_username = StringField()
    twitter_profile_picture = StringField()

    meta = {
        'indexes': ['email', 'facebook_id', 'twitter_id'],
        'allow_inheritance': True,
        }

    def validate(self):
        super(User, self).validate()
        if not any([self.facebook_id, self.twitter_id, self.email]):
            raise ValidationError(
                "email, facebook_id or twitter_id must exist"
            )

        # Check for uniqueness of email and social IDs.
        for field in ("facebook_id", "twitter_id", "email"):
            value = getattr(self, field)
            if value:
                existing = User.objects(**{field: value}).all()
                if len(existing) > 1 or \
                        existing and existing[0] != self:
                    raise ValidationError("Duplicate %s: %s" % (field, value))

    def get_profile_picture(self):
        """
        Returns a profile picture either based on twitter, facebook or email
        based gravatar
        """
        if self.facebook_picture:
            return self.facebook_picture
        if self.twitter_profile_picture:
            return self.twitter_profile_picture
        if self.email:
            return self.get_gravatar()
        return u''

    def get_gravatar(self, default=None, size=40):
        """
        Gets the gravatar for the user based on the email
        """
        url = 'https://secure.gravatar.com/avatar/%s?'
        url = url % hashlib.md5(self.email.lower()).hexdigest()

        params = []
        if default:
            params.append(('d', default))
        if size:
            params.append(('s', str(size)))

        return url + urllib.urlencode(params)

    @staticmethod
    def make_hash(password, salt):
        """
        Returns hashed hexdigest of given password and salt
        """
        password += salt
        if isinstance(password, unicode):
            password = password.encode('utf-8')
        password_sha = hashlib.sha1(password).hexdigest()
        return password_sha

    def set_password(self, password):
        """
        Set the password of the given user
        """
        self.salt = ''.join(
            random.sample(string.ascii_letters + string.digits, 8)
        )
        self.password = self.make_hash(password, self.salt)

    @staticmethod
    def authenticate(email, password):
        """
        Tries to authenticate a user

        :return:    None if user not found
                    False if password is wrong
                    User object/document if correct
        """
        user = User.objects(email=email).first()
        if not user:
            return None

        if not user.password:
            return False

        if user.password == User.make_hash(password, user.salt):
            return user

        return False

    def aslocaltime(self, naive_date):
        """
        Returns a localized time using `pytz.astimezone` method.

        :param naive_date: a naive datetime (datetime with no timezone
            information), which is assumed to be the UTC time.
        :return: A datetime object with the local time.
        """
        utc_date = pytz.utc.localize(naive_date)

        user_tz = pytz.timezone(self.timezone)
        if user_tz == pytz.utc:
            return utc_date

        return utc_date.astimezone(user_tz)
