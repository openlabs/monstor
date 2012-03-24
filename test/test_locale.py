# -*- coding: utf-8 -*-
"""
    test_locale

    test the locale

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
import unittest2 as unittest

import pycountry
from tornado.web import Application
from tornado.testing import AsyncHTTPTestCase
from monstor.utils.web import BaseHandler
from monstor.utils.i18n import _


class TestLocale(unittest.TestCase):

    def test_0010_load_gettext(self):
        """
        Load the translations from pycountry to test
        """
        from monstor.utils import locale
        locale.load_gettext_translations(pycountry.LOCALES_DIR, 'iso3166')
        self.assertTrue("es" in locale._supported_locales)
        t = locale.get("pt_BR")
        self.assertEqual(t.translate("United States"), u'Estados Unidos')
        t = locale.get("pt")
        self.assertEqual(t.translate("United States"), u'Estados Unidos')
        t = locale.get("es")
        self.assertEqual(t.translate("United States"), u'Estados Unidos')


class TestLocaleLoading(AsyncHTTPTestCase, unittest.TestCase):

    def get_app(self):
        class TranslationTestHandler(BaseHandler):
            def get(self):
                self.write(unicode(self._("United States")))

        class UsingGlobalTranslationHandler(BaseHandler):
            def get(self):
                message = _("United States")
                self.write(unicode(message))

        return Application(
            [
                ('/1', TranslationTestHandler),
                ('/2', UsingGlobalTranslationHandler),
            ],
            cookie_secret="something_really_random"
        )

    def test_0020_loc_with_url_arg(self):
        """
        Test the locale identification based on URL parameter
        """
        self.assertEqual(self.fetch('/1', method="GET").body, u'United States')
        self.assertEqual(
            self.fetch('/1?locale=pt', method="GET").body,
            u'Estados Unidos'
        )

    def test_0030_global(self):
        """
        Test the locale identification based on URL parameter
        """
        self.assertEqual(self.fetch('/2', method="GET").body, u'United States')
        self.assertEqual(
            self.fetch('/2?locale=pt', method="GET").body,
            u'Estados Unidos'
        )
        self.assertEqual(
            self.fetch('/2?locale=es', method="GET").body,
            u'Estados Unidos'
        )
        self.assertEqual(
            self.fetch('/2?locale=fr', method="GET").body,
            '\xc3\x89tats-Unis'
        )


if __name__ == '__main__':
    unittest.main()
