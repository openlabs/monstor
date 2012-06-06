# -*- coding: utf-8 -*-
"""
    web

    Web components and helpers

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
import json
from collections import defaultdict

import tornado.web
from monstor.utils import locale
from speaklater import make_lazy_gettext


class BaseHandler(tornado.web.RequestHandler):

    #: The messages which are yet to be written, but needs to be shown if a
    #: local flash_message is called
    #: Do not set this variable directly, use the helper methods instead
    _messages = None

    def get_user_model(self):
        try:
            return self.application.settings['user_model']
        except KeyError:
            from monstor.contrib.auth.models import User
            return User

    @property
    def locale(self):
        """The local for the current session.

        Determined by either get_user_locale, which you can override to
        set the locale based on, e.g., a user preference stored in a
        database, or get_browser_locale, which uses the Accept-Language
        header.
        """
        if not hasattr(self, "_locale"):
            self._locale = self.get_user_locale()
            if not self._locale:
                self._locale = self.get_browser_locale()
                assert self._locale
        return self._locale



    def prepare(self):
       from monstor.utils.i18n import t
       t.clear()
       t.appendleft(self.locale)

    @property
    def _(self):
        return make_lazy_gettext(lambda: self.locale.translate)

    def get_user_locale(self):
        """
        Tries to identify the user locale in the following order. If not found
        in any of them, None is returned. On returning None the browser Accept
        headers are used to identify the language

        1. Look for the locale in the user object if user is logged in
        2. Look for the locale in the cookie
        3. Look for the locale in the url in the args (locale)
        """
        # 1. Look for the locale in the cookie
        cookie_locale = self.get_secure_cookie('locale')
        if cookie_locale:
            return locale.get(cookie_locale)

        # 2. Look for the locale in the url
        url_locale = self.get_argument('locale', default=None)
        if url_locale:
            return locale.get(url_locale)

        if self.current_user is None:
            return None # Fallback to browser based locale detection

        # 3. Look for the locale in the user object if user is logged in
        if self.current_user and self.current_user.locale:
            return locale.get(self.current_user.locale)

        # 4. Fallback to browser based locale detection
        return None

    def get_browser_locale(self, default="en_US"):
        """Determines the user's locale from Accept-Language header.

        See http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.4
        """
        if "Accept-Language" in self.request.headers:
            languages = self.request.headers["Accept-Language"].split(",")
            locales = []
            for language in languages:
                parts = language.strip().split(";")
                if len(parts) > 1 and parts[1].startswith("q="):
                    try:
                        score = float(parts[1][2:])
                    except (ValueError, TypeError):
                        score = 0.0
                else:
                    score = 1.0
                locales.append((parts[0], score))
            if locales:
                locales.sort(key=lambda (l, s): s, reverse=True)
                codes = [l[0] for l in locales]
                return locale.get(*codes)
        return locale.get(default)

    def get_current_user(self):
        """
        Find user from secure cookie
        """
        user_id = self.get_secure_cookie("user")
        if not user_id:
            return None
        User = self.get_user_model()
        return User.objects().with_id(user_id)

    @property
    def messages(self):
        if self._messages is None:
            self._messages = defaultdict(
                list, json.loads(
                    self.get_secure_cookie('flash_messages') or '{}'
                )
            )
        return self._messages

    @messages.setter
    def messages(self, value):
        if value is None:
            value = defaultdict(list)
        self._messages = value
        self.set_secure_cookie(
            'flash_messages', json.dumps(dict(self._messages))
        )

    def get_flashed_messages(self, category, destroy=True):
        """
        :param destroy: Should the messages be discarded after its fetched
        """
        messages = self.messages

        if destroy:
            messages_copy = self.messages.copy()
            messages_copy[category] = []
            self.messages = messages_copy

        return messages.get(category, [])

    def get_all_messages(self, destroy=True):
        """
        :param destroy: Should the messages be discarded after its fetched
        """
        messages = self.messages

        if destroy:
            self.messages = None

        return messages.iteritems()

    def flash(self, message, category='default'):
        """
        flash messages of a category by calling `self.flash('message', 'cat')`

        For exmaple:

            self.flash("Welcome to our website", "info")

        """
        messages = self.messages.copy()
        messages[category].append(unicode(message))
        self.messages = messages

    def render_string(self, template_name, **kwargs):
        """
        Put the get_flashed_messages in template render context
        """
        return super(BaseHandler, self).render_string(
            template_name, get_flashed_messages=self.get_flashed_messages, 
            get_all_messages=self.get_all_messages,
            **kwargs
        )

    is_xhr = property(
        lambda x: x.get_argument("X-Requested-With", "").\
            lower() == "xmlhttprequest",
            doc="""Detailed Documentation"""
    )
