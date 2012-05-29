# -*- coding: utf-8 -*-
"""
    app

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) LTD
    :license: BSD, see LICENSE for more details.
"""
from tornado import options
from tornado.web import Application
from mongoengine import connect

from monstor.exc import InvalidRequestError

options.define("config", help="Config file relative path")
options.define("login_url", default="/login", help="Login url for application")
options.define('cookie_secret', help="Secret for setting the secure cookie")
options.define('address', default="127.0.0.1", help="Address to bind to")
options.define('port', default=8000, type=int, help="Port to listen")

# Database settings
options.define("database", default=None, help="Database name")
options.define("db_host", default="localhost",
    help="Host name where mongod runs"
)
options.define("db_port", default=27017, help="Port where mongod listen to")
options.define("db_username", help="Username to connect to MongoDB")
options.define("db_password", help="Username to connect to Paassword")

DEFAULT_SETTINGS = {
    'xsrf_cookies': True,
}

def load_app(app_name):
    """
    Loads the application

    :param app_name: The string name of the module that needs to be imported
    :return: The list of handlers
    """
    app = __import__(app_name, fromlist=['models', 'urls', 'ui_modules'])

    handlers = []
    if hasattr(app, 'urls') and hasattr(app.urls, 'HANDLERS'):
        handlers = app.urls.HANDLERS

    ui_modules = {}
    if hasattr(app, 'ui_modules') and hasattr(app.ui_modules, 'UI_MODULES'):
        ui_modules = app.ui_modules.UI_MODULES

    return handlers, ui_modules


def make_app(default_host='', transforms=None, wsgi=False, **settings):
    """
    Builds an instance of :class:`tornado.web.Application` and returns it 
    with the configuration steps completed. The handlers are automatically
    picked up from the `installed_apps` setting in the settings.

    Remember that the modules are loaded in the order of the list and it
    affects the overall way the application works including how the URLs
    are resolved.
    """
    options.parse_command_line()
    config_file = options.options.config
    if config_file:
        options.parse_config_file(config_file)

    app_settings = DEFAULT_SETTINGS
    app_settings.update(settings)

    # XXX: Check again if DB must be loaded after or before apps
    if not options.options.database:
        raise InvalidRequestError("Database not specified in options")
    connect(
        options.options.database, host=options.options.db_host,
        port=options.options.db_port, username=options.options.db_username,
        password=options.options.db_password
    )

    handlers = []
    ui_modules = {}
    for app_name in settings['installed_apps']:
        app_handlers, app_ui_modules = load_app(app_name)
        handlers.extend(app_handlers)
        ui_modules.update(app_ui_modules)

    app_settings.setdefault('ui_modules', {}).update(ui_modules)

    application = Application(
        handlers, default_host, transforms, wsgi, **app_settings
    )
    return application
