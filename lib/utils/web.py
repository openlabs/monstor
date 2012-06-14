# -*- coding: utf-8 -*-
"""
    web

    Web components and helpers

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
import json
from collections import defaultdict
import re
from math import ceil
from copy import copy
import smtplib

import tornado.web
from tornado import options
from monstor.utils import locale
from speaklater import make_lazy_gettext
from unidecode import unidecode

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')


def slugify(text, delim=u'-'):
    """
    Generates an ASCII-only slug.
    """
    result = []
    for word in _punct_re.split(text.lower()):
        result.extend(unidecode(word).split())
    return unicode(delim.join(result))


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

    def send_mail(self, sender, receiver, message):
        """
        Send email to receiver

        :param sender: email Id of the sender
        :param receiver: email Id of the receiver
        :param message: email content
        """
        if options.options.smtp_ssl:
            smtp_server = smtplib.SMTP_SSL(
                options.options.smtp_server, options.options.smtp_port
            )
        else:
            smtp_server = smtplib.SMTP(
                options.options.smtp_server, options.options.smtp_port
            )
        if options.options.smtp_tls:
            smtp_server.starttls()
        if options.options.smtp_user and options.options.smtp_password:
            smtp_server.login(
                options.options.smtp_user, options.options.smtp_password
            )
        smtp_server.sendmail(sender, receiver, message)
        smtp_server.quit()


class Pagination(object):
    """
    A pagination object which works with Mongoengine Query Sets
    """

    def __init__(self, page, per_page, query_set):
        """
        :param page: The page to be displayed
        :param per_page: Items per page
        :param query_set: The query set based on which pagination is to be done
        """
        self.page = page
        self.per_page = per_page
        self.query_set = query_set

    @property
    def count(self):
        "Returns the total number of records in the query set"
        return self.query_set.count()

    def all_items(self):
        """Returns complete set of items

        .. warning::
            This can end up being very inefficient depending upon the
            number of records
        """
        return self.query_set.all()

    def items(self):
        """Returns the list of items in current page
        """
        qs_copy = copy(self.query_set)
        return qs_copy[self.offset:self.offset + self.per_page]

    def __iter__(self):
        for item in self.items():
            yield item

    def __len__(self):
        return self.count

    def prev(self):
        """Returns a :class:`Pagination` object for the previous page."""
        return Pagination(self.page - 1, self.per_page, self.query_set)

    def next(self):
        """Returns a :class:`Pagination` object for the next page."""
        return Pagination(self.page + 1, self.per_page, self.query_set)

    #: Attributes below this may not require modifications in general cases

    def iter_pages(self, left_edge=2, left_current=2,
                    right_current=2, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
        This is how you could render such a pagination in the templates:

        .. sourcecode:: html+jinja

            <div class=pagination>
            {%- for page in pagination.iter_pages() %}
                {% if page %}
                    {% if page != pagination.page %}
                        <a href="{{ reverse_url(endpoint, page=page) }}">{{ page }}</a>
                    {% else %}
                        <strong>{{ page }}</strong>
                    {% endif %}
                {% else %}
                    <span class=ellipsis>…</span>
                {% end %}
            {%- end %}
            </div>
        """
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
                (num > self.page - left_current - 1 and \
                 num < self.page + right_current) or \
                num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

    offset = property(lambda self: (self.page - 1) * self.per_page)

    prev_num = property(lambda self: self.page - 1)
    has_prev = property(lambda self: self.page > 1)

    next_num = property(lambda self: self.page + 1)
    has_next = property(lambda self: self.page < self.pages)

    pages = property(lambda self: int(ceil(self.count / float(self.per_page))))

    begin_count = property(lambda self: min([
        ((self.page - 1) * self.per_page) + 1,
        self.count]))
    end_count = property(lambda self: min(
        self.begin_count + self.per_page - 1, self.count))
