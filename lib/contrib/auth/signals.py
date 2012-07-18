# -*- coding: utf-8 -*-
"""
    signals

    Create signals based on login success and login failure

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from blinker import signal

login_success = signal('monstor.contrib.auth.login.success')
login_failure = signal('monstor.contrib.auth.login.failure')
