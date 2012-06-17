# -*- coding: utf-8 -*-
"""
    setup

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
from setuptools import setup, find_packages
from itertools import izip, repeat

setup(
    name = "monstor",
    version = "0.2dev",
    description = "Tornado and MongoDB web framework",

    author = "Openlabs Technologies & Consulting (P) Limited",
    author_email = "sales@openlabs.co.in",
    url = "http://openlabs.co.in",
    license = "BSD",

    install_requires = [
        "distribute",
        "tornado>2.1,<2.3",
        "mongoengine",
        "babel",
        "requests",
        "unittest2",
        "speaklater",
        "wtforms",
        "unidecode",
        "pytz",
    ],
    packages = ['monstor'] + map(
        '.'.join, izip(repeat('monstor'), find_packages('lib'))
    ),
    package_dir = {
        'monstor': 'lib'
    },
    scripts = [
        'scripts/monstor_admin',
    ],
    zip_safe=False,
    classifiers = [
        "Development Status :: 1 - Planning",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
    ],
)
