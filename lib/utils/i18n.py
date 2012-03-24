# -*- coding: utf-8 -*-
"""
    i18n

    Internationalisation of Monstor. The locale support of tornado as such
    is pretty basic and does not offer support for merging translation
    catalogs and several other features most large application require.

    This module tries to retain the same API as that of tornado.locale but
    tries to implement the features with the support of babel.

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""

from __future__ import absolute_import
from collections import deque
from speaklater import is_lazy_string, make_lazy_string


t = deque(maxlen=1)

def gettext(string, **variables):
    """Translates a string with the current locale and passes in the
    given keyword arguments as mapping to a string formatting string.

    ::

        gettext(u'Hello World!')
        gettext(u'Hello %(name)s!', name='World')
    """
    global t
    if not t:
        return string % variables
    return t[0].translate(string) % variables


def ngettext(singular, plural, n, **variables):
    """Translates a string with the current locale and passes it to the 
    ngettext API of the translations object
    """
    global t
    variables.setdefault('num', n)
    if not t:
        return (plural if n > 1 else singular) % variables
    return t[0].ungettext(singular, plural, n) % variables


def make_lazy_gettext(lookup_func):
    """Creates a lazy gettext function dispatches to a gettext
    function as returned by `lookup_func`.

    :copyright: (c) 2010 by Armin Ronacher.

    Example:

    >>> translations = {u'Yes': u'Ja'}
    >>> lazy_gettext = make_lazy_gettext(lambda: translations.get)
    >>> x = lazy_gettext(u'Yes')
    >>> x
    lu'Ja'
    >>> translations[u'Yes'] = u'Si'
    >>> x
    lu'Si'
    """
    def lazy_gettext(string, *args, **kwargs):
        if is_lazy_string(string):
            return string
        return make_lazy_string(lookup_func(), string, *args, **kwargs)
    return lazy_gettext

_, N_ = make_lazy_gettext(lambda: gettext), make_lazy_gettext(lambda: ngettext)
