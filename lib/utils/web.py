# -*- coding: utf-8 -*-
"""
    web

    Web components and helpers

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
import json

import tornado.web
from monstor.utils import locale
from speaklater import make_lazy_gettext


class BaseHandler(tornado.web.RequestHandler):

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

    def get_flashed_messages(self, category=None, destroy=True):
        """
        :param destroy: Should the messages be discarded after its fetched
        """
        messages = self.get_secure_cookie('flash_messages') or '{}'
        if destroy:
            self.set_flashed_message_category(category, None)
        return json.loads(messages).setdefault(category, [])

    def get_all_messages(self, destroy=True):
        """
        :param destroy: Should the messages be discarded after its fetched
        """
        messages = self.get_secure_cookie('flash_messages') or '{}'
        if destroy:
            self.set_secure_cookie('flash_messages', '{}')
        return json.loads(messages).iteritems()

    def set_flashed_message_category(self, category, value):
        """
        Sets the value of a specific message category

        :param category: Name of the category
        :param value: The list of messages
        """
        if value is None:
            value = []
        messages = self.get_secure_cookie('flash_messages') or '{}'
        messages_dict = json.loads(messages)
        messages_dict[category] = value
        self.set_secure_cookie('flash_messages', json.dumps(messages_dict))

    def flash(self, message, category=None):
        """
        flash messages of a category by calling `self.flash('message', 'cat')`

        For exmaple:

            self.flash("Welcome to our website", "info")

        """
        messages = self.get_flashed_messages(category=category, destroy=False)
        messages.append(unicode(message))
        self.set_flashed_message_category(category, messages)

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
