# -*- coding: utf-8 -*-
"""
    exc

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
import traceback


class MonstorError(Exception):
    """Generic error class"""


class InvalidRequestError(MonstorError):
    """Monstor was asked to do something it can't do.

    This error generally corresponds to runtime state errors.
    """
