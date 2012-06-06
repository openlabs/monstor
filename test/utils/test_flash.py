# -*- coding: utf-8 -*-
"""
    test_flash

    Test the flashing of messages

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from tempfile import NamedTemporaryFile
import unittest
from tornado.web import Application
from tornado.testing import AsyncHTTPTestCase
from monstor.utils.web import BaseHandler


class TestFlash(AsyncHTTPTestCase, unittest.TestCase):

    def get_app(self):

        with NamedTemporaryFile(delete=False) as file:
            file.write("""
                {% for category, message in get_all_messages() %}
                {{ category }}, {{ message }}
                {% end %}
            """)
        template_path = file.name

        class FlashButWriteHandler(BaseHandler):
            def get(self):
                self.flash("flash")
                self.write("I will not call get_messages")

        class FlashTestRenderHandler(BaseHandler):
            def get(self):
                self.flash("flash")
                self.render(template_path)

        class FlashTestRedirectHandler(BaseHandler):
            def get(self):
                self.flash("flash2")
                self.redirect("/redirect-no-flash")

        class FlashTestRedirectNoFlashHandler(BaseHandler):
            def get(self):
                self.redirect("/render2")

        class FlashTestRenderHandler2(BaseHandler):
            def get(self):
                self.flash("flash3")
                self.render(template_path)

        return Application(
            [
                (r'/just-write', FlashButWriteHandler),
                (r'/render', FlashTestRenderHandler),
                (r'/redirect', FlashTestRedirectHandler),
                (r'/redirect-no-flash', FlashTestRedirectNoFlashHandler),
                (r'/render2', FlashTestRenderHandler2),
            ],
            cookie_secret="something_really_random"
        )

    def test_0005_write(self):
        self.assertTrue(
            'Set-Cookie' in self.fetch('/just-write', method="GET").headers
        )

    def test_0010_render(self):
        """
        Test that when a page is rendered it shows flashed messages but not on
        subsequent requests
        """
        self.assertEqual(
            self.fetch('/render', method="GET").body.count('flash'), 1
        )

        # This is not a typo, its calling again
        self.assertEqual(
            self.fetch('/render', method="GET").body.count('flash'), 1
        )


    def test_0020_redirect(self):
        """
        When a redirect happens after a flash, the message shuld remain in the
        cookie and displayed on the next render, even if there
        """
        rv = self.fetch('/render2', method="GET")
        self.assertEqual(rv.code, 200)
        self.assertEqual(rv.body.count('flash3'), 1)

        headers = {
            'Cookie':'flash_messages="eyJkZWZhdWx0IjogWyJmbGFzaCJdfQ==|1338974405|267abbaf58a1dfaea1550236d6f9a59ecc0db933"; expires=Fri, 06 Jul 2012 09:20:05 GMT; Path=/'
        }
        rv = self.fetch('/render2', method="GET", headers=headers)
        self.assertEqual(rv.code, 200)
        self.assertEqual(rv.body.count('flash'), 2)
        self.assertEqual(rv.body.count('flash3'), 1)


if __name__ == '__main__':
    unittest.main()
