# -*- coding: utf-8 -*-
"""
    urls

    URLs in the application

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import tornado.web

from monstor.contrib.auth.views import (FacebookLoginHandler, GoogleHandler,
    TwitterHandler, LoginHandler, LogoutHandler, RegistrationHandler,
    AccountActivationHandler, ActivationKeyResendHandler)

U = tornado.web.URLSpec

HANDLERS = [
    U(r'/auth/facebookgraph', FacebookLoginHandler, name="contrib.auth.facebook"),
    U(r'/auth/google', GoogleHandler, name="contrib.auth.google"),
    U(r'/auth/twitter', TwitterHandler, name="contrib.auth.twitter"),
    U(r'/login', LoginHandler, name='contrib.auth.login'),
    U(r'/logout', LogoutHandler, name='contrib.auth.logout'),
    U(r'/registration', RegistrationHandler, name='contrib.auth.registration'),
    U(r'/activation/([a-zA-Z0-9\._]+)', AccountActivationHandler,
        name="contrib.auth.activation"),
    U(r'/activation_resend', ActivationKeyResendHandler,
        name="contrib.auth.activation_resend"),
]
