# -*- coding: utf-8 -*-
"""
    wtforms

    WTForms reusable components

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from __future__ import absolute_import
from wtforms import validators
from monstor.utils.i18n import _


class TornadoMultiDict(object):
    """A wrapper to make the tornado request handler to be compatible with the
    multidict format used by WTForms
    """

    def __init__(self, handler):
        self.handler = handler

    def __iter__(self):
        return iter(self.handler.request.arguments) 

    def __len__(self):
        return len(self.handler.request.arguments) 

    def __contains__(self, name):
        return (name in self.handler.request.arguments) 

    def getlist(self, name):
        return self.handler.get_arguments(name, strip=False) 


REQUIRED_VALIDATOR = validators.Required(message=_("This field is required"))
EMAIL_VALIDATOR = validators.Email(message=_('Invalid email address'))
