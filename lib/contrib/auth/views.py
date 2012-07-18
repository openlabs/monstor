# -*- coding: utf-8 -*-
"""
    views

    Authentication Request Handlers

    :copyright: (c) 2012 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
import string
import random
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import tornado.web
import tornado.auth
from tornado.options import define, options
from mongoengine import Q
from wtforms import Form, TextField, PasswordField, validators
from itsdangerous import URLSafeSerializer

from monstor.utils.wtforms import REQUIRED_VALIDATOR, EMAIL_VALIDATOR, \
    TornadoMultiDict
from monstor.utils.web import BaseHandler
from monstor.utils.i18n import _
from monstor.contrib.auth.signals import login_success, login_failure

define("require_activation", type=bool,
    help="Email activation will be made mandatory for new manual\
    registrations.", default=False)
define("twitter_consumer_key", help="Twitter consumer key")
define("twitter_consumer_secret", help="Twitter consumer secret")

define("facebook_api_key", help="Facebook application API key")
define("facebook_secret", help="Facebook application secret")

# pylint: disable=R0904
# -- Too many public methods
# pylint: disable=R0903
# -- Too few public methods

logger = logging.getLogger(__name__)


class ActivationKeyMixin(object):
    """
    A mixin class which makes it possible to create an activation key and
    send it to the user.
    """
    def create_activation_key(self, user):
        """
        Build an account activation key and build the email
        """
        signer = URLSafeSerializer(self.application.settings["cookie_secret"])
        activation_key = signer.dumps(user.email)
        parts = []
        try:
            parts.append(
                MIMEText(
                    self.render_string(
                        'emails/activation-html.html',
                        activation_key=activation_key
                    ), 'html'
                )
            )
        except IOError:
            logging.warning('No HTML template emails/activation-html.html')

        try:
            parts.append(
                MIMEText(
                    self.render_string(
                        "emails/activation-text.html",
                        activation_key=activation_key
                    ), 'text'
                )
            )
        except IOError:
            logging.warning("No TEXT template emails/activation-text.html")
        if not parts:
            # Fallback to simple string replace since no templates have been
            # defined.
            parts.append(
                MIMEText(
                    'To activate click: %s' %
                    self.reverse_url('contrib.auth.activation', activation_key)
                    , 'text'
                )
            )
        message = MIMEMultipart('alternative')
        message['Subject'] = _("Activate your Account")
        message['From'] = options.email_sender
        message['To'] = user.email
        for part in parts:
            message.attach(part)
        self.send_mail(options.email_sender, user.email, message.as_string())


class RegistrationForm(Form):
    """Traditional Registration Form"""
    company_name = TextField(_('Company Name'))
    name = TextField(_('Name'), [REQUIRED_VALIDATOR])
    email = TextField(_('Email'), [EMAIL_VALIDATOR, REQUIRED_VALIDATOR])
    password = PasswordField(
        _("Password"), [
            REQUIRED_VALIDATOR,
            validators.EqualTo(
                'confirm_password', message=_('Passwords must match')
            )
        ]
    )
    confirm_password = PasswordField(
        _("Confirm Password"), [REQUIRED_VALIDATOR, ]
    )


class RegistrationHandler(BaseHandler, ActivationKeyMixin):
    """
    Regular username and password based authentication
    """
    def get(self):
        """
        Render the registration page
        """
        if self.get_current_user():
            self.redirect(
                self.get_argument('next', None) or \
                    self.application.reverse_url("home")
            )
            return
        self.render(
            'user/registration.html', registration_form=RegistrationForm()
        )
        return

    def post(self):
        """
        Accept registrations
        """
        User = self.get_user_model()
        form = RegistrationForm(TornadoMultiDict(self))
        if form.validate():
            # First check if user exists
            user = User.objects(email=form.email.data).first()
            if user:
                self.flash(_(
                        "This email is already registered. Click on Sign In"
                    ), "warning"
                )
            else:
                user = User(
                    company_name = form.company_name.data,
                    name = form.name.data,
                    email = form.email.data,
                )
                user.set_password(form.password.data)
                user.save(safe=True)
                if options.require_activation:
                    self.create_activation_key(user)
                    self.flash(
                        _("Thank you for registering %(name)s. Please check\
                            your Inbox and follow the instructions",
                            name=user.name), 'info'
                    )
                    self.redirect(self.reverse_url("home"))
                    return
                else:
                    user.active = True
                    user.save()
                    self.flash(
                       _("Thank you for registering %(name)s", name=user.name),
                        'info'
                    )
                    self.set_secure_cookie("user", unicode(user.id))
                    self.redirect(
                        self.get_argument('next', None) or \
                            self.reverse_url("home")
                    )
                    return
        else:
            self.flash(
                _("There were error(s) in processing your registration."),
                'error'
            )
        self.render('user/registration.html', registration_form=form)


class LoginForm(Form):
    """Traditional Login Form"""

    email = TextField(_('Email'), [EMAIL_VALIDATOR, REQUIRED_VALIDATOR])
    password = PasswordField(_("Password"), [REQUIRED_VALIDATOR])


class LoginHandler(BaseHandler):
    """Renders the login page"""

    def get(self):
        """
        Render the login page
        """
        if self.get_current_user():
            self.redirect(
                self.get_argument('next', None) or \
                    self.application.reverse_url("home")
            )
            return
        self.render('user/login.html', login_form=LoginForm())
        return

    def post(self):
        """
        Try to authenticate the user and log the user if successful
        """
        User = self.get_user_model()
        form = LoginForm(TornadoMultiDict(self))
        if form.validate():
            user = User.authenticate(form.email.data, form.password.data)
            if user:
                if options.require_activation and not user.active:
                    self.flash(
                        _("User not activated yet, please activate your\
                            account"
                        ), "warning"
                    )
                    self.redirect(
                        self.reverse_url("contrib.auth.activation_resend")
                    )
                    return
                self.set_secure_cookie("user", unicode(user.id))
                login_success.send(self, user=user)
                self.flash(_("Welcome back %(name)s", name=user.name), 'info')
                self.redirect(
                    self.get_argument('next', None) or \
                        self.reverse_url("home")
                )
                return
            login_failure.send(self)
            self.flash(_("The email or password is invalid"), 'error')
        self.render('user/login.html', login_form=form)


class LogoutHandler(BaseHandler):
    """Logout"""

    def get(self):
        """
        Clear the cookie and hence log the user out
        """
        self.clear_cookie("user")
        self.redirect(self.application.reverse_url("home"))


class GoogleHandler(BaseHandler, tornado.auth.GoogleMixin):
    """
    Google authentication
    """

    @tornado.web.asynchronous
    def get(self):
        """Entry point for google auth
        """
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user_data):
        """
        Callback Function
        """
        User = self.get_user_model()
        logger.info(user_data)

        if not user_data:
            login_failure.send(self)
            self.flash(_("Login using Google failed, please try again"))
            self.redirect(self.application.reverse_url("contrib.auth.login"))
            self.finish()

        logger.info(user_data)

        user = User.objects(email=user_data['email']).first()
        if user:
            self.flash(_("Welcome back %(name)s", name=user.name), 'info')
        else:
            user = User(
                name = user_data['name'],
                email = user_data['email'],
                )
            user.save()
            self.flash(
                _("Thank you for regsitering %(name)s", name=user.name)
            )

        self.set_secure_cookie("user", unicode(user.id))
        login_success.send(self, user=user)

        # Finally issue a redirect if the login was successful
        self.redirect(
            self.get_argument('next', None) or \
                self.application.reverse_url("home")
        )


class TwitterHandler(BaseHandler, tornado.auth.TwitterMixin):
    """
    Twitter Authentication handler
    """
    @tornado.web.asynchronous
    def get(self):
        """Entry point"""
        User = self.get_user_model()
        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authorize_redirect()

    def _on_auth(self, user_data):
        """Call back handler for twitter authentication"""
        User = self.get_user_model()
        logger.info(user_data)

        if not user_data:
            login_failure.send(self)
            self.flash(_("Login using Twitter failed, please try again"))
            self.redirect(self.application.reverse_url("contrib.auth.login"))
            self.finish()

        logging.info(user_data)

        user = User.objects(twitter_username=user_data['username']).first()
        if user:
            self.flash(_("Welcome back %(name)s", name=user.name), 'info')
        else:
            user = User(
                name = user_data['name'],
                twitter_id = user_data['id_str'],
                twitter_username = user_data['username'],
                twitter_profile_picture = user_data['profile_image_url_https'],
                twitter_description = user_data['description'],
                )
            user.save()
            self.flash(
                _("Thank you for registering %(name)s", name=user.name)
            )

        self.set_secure_cookie("user", unicode(user.id))
        login_success.send(self, user=user)

        # Finally redirect to the home page once the user has been created
        self.redirect(
            self.get_argument('next', None) or \
                self.application.reverse_url("home")
        )

    def _oauth_consumer_token(self):
        """
        Reimplement so that thse are fetched from options rather than settings
        """
        return dict(
            key=options.twitter_consumer_key,
            secret=options.twitter_consumer_secret
        )


class FacebookLoginHandler(BaseHandler, tornado.auth.FacebookGraphMixin):
    """Facebook Authentication"""

    @tornado.web.asynchronous
    def get(self):
        redirect_uri = ''.join((
            self.request.protocol,
            '://',
            self.request.host,
            self.reverse_url('contrib.auth.facebook'),
        ))
        if self.get_argument("code", False):
            # If there is a code argument in the URL then it's a return from 
            # facebook. Then send it back to facebook and get information about
            # the user from facebook
            self.get_authenticated_user(
                redirect_uri = redirect_uri,
                client_id = options.facebook_api_key,
                client_secret = options.facebook_secret,
                code = self.get_argument("code"),
                extra_fields = ['email', 'username'],
                callback = self.async_callback(self._on_login))
            return

        self.authorize_redirect(
            redirect_uri = redirect_uri,
            client_id = options.facebook_api_key,
            extra_params = {
                "scope": "user_about_me,user_location,"
                         "user_hometown,user_status,"
                         "email"
                }
            )

    def _on_login(self, user_data):
        """
        Callback function to handle facebook response
        """
        User = self.get_user_model()
        logger.info(user_data)

        if not user_data:
            login_failure.send(self)
            self.flash(_("Login using Facebook failed, please try again"))
            self.redirect(self.application.reverse_url("contrib.auth.login"))
            self.finish()


        user = User.objects(
            Q(facebook_id=int(user_data['id'])) | Q(email=user_data['email'])
        ).first()

        if user:
            self.flash(_("Welcome back %(name)s", name=user.name), 'info')
            if not user.facebook_id:
                user.facebook_id = user_data['id']
                user.facebook_picture = user_data['picture']
                user.facebook_username = user_data['username']
                user.facebook_link = user_data['link']
                user.save()
                self.flash(
                    _("Your facebook account is now connected to your account")
                )
        else:
            user = User(
                facebook_id = user_data['id'],
                facebook_picture = user_data['picture'],
                facebook_username = user_data['username'],
                facebook_link = user_data['link'],
                name = user_data['name'],
                email = user_data['email']
                )
            user.save()
            self.flash(
                _("Thank you for registering %(name)s", name=user.name)
            )

        self.set_secure_cookie("user", unicode(user.id))
        login_success.send(self, user=user)

        self.redirect(
            self.get_argument('next', None) or \
                self.application.reverse_url("home")
        )


class AccountActivationHandler(BaseHandler):
    """
    Activate the user account
    """
    def get(self, activation_key):
        """
        Acccept the Activation key from url and activate the user account
        """
        signer = URLSafeSerializer(self.application.settings["cookie_secret"])
        User = self.get_user_model()
        user = User.objects(email=signer.loads(activation_key)).first()
        if not user:
            self.flash(
                _('Invalid Activation Key, Please register.'), 'warning'
            )
            self.redirect(self.reverse_url("contrib.auth.registration"))
            return
        user.active = True
        user.save()
        self.flash(
            _("Thank you for activating your account. Please login again."),
            'info'
        )
        self.redirect(self.reverse_url('contrib.auth.login'))


class ActivationResendForm(Form):
    """Activation key resend Form"""

    email = TextField(_('Email'), [EMAIL_VALIDATOR, REQUIRED_VALIDATOR])


class ActivationKeyResendHandler(BaseHandler, ActivationKeyMixin):
    """
    Resend the activation key
    """
    def get(self):
        """
        Renders a page for activation key regeneration
        """
        form = ActivationResendForm(
            email=self.get_argument('email', default=None)
        )
        self.render('user/activation_resend.html', form=form)
        return

    def post(self):
        """
        Accept the email Id from the user and create a new activation key
        also send it to the given email id.
        """
        User = self.get_user_model()
        form = ActivationResendForm(TornadoMultiDict(self))
        if form.validate():
            user = User.objects(email=form.email.data).first()
            if user:
                self.create_activation_key(user)
                self.flash(
                    _("An email has been send to the given email Id. Please\
                    check your inbox and follow the instructions ")
                )
                self.redirect(self.reverse_url('contrib.auth.login'))
                return
            self.flash(
                _("Oops! we could not match your email with any of our users"),
                "error"
            )
        self.render('user/activation_resend.html', form=form)


class SendPasswordResetForm(Form):
    """Send the password reset key for email provided
    """
    email = TextField('Email', [EMAIL_VALIDATOR, REQUIRED_VALIDATOR])


class SendPasswordResetKeyHandler(BaseHandler):
    """Sends the password reset key
    """

    def get(self):
        "Render the form"
        form = SendPasswordResetForm(TornadoMultiDict(self))

        return self.render('user/send_reset_key.html', form=form)

    def send_password_reset_mail(self, user):
        """Send the Beta Registration Confirmation Email
        """
        # Create message container, the correct MIME type is
        # multipart/alternative.
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Reset your account password"
        msg['From'] = options.email_sender
        msg['To'] = user.email

        # Create the body of the message (a plain-text and an HTML version).
        # text is your plain-text email
        # html is your html version of the email
        # if the reciever is able to view html emails then only the html
        # email will be displayed

        parts = []
        try:
            parts.append(
                MIMEText(
                    self.render_string(
                        'emails/send_password_reset_mail_html.html',
                        user=user
                    ), 'html'
                )
            )
        except IOError:
            logging.warning(
                'No HTML template emails/send_password_reset_mail_html.html'
            )

        try:
            parts.append(
                MIMEText(
                    self.render_string(
                        "emails/send_password_reset_mail_text.html",
                        user=user
                    ), 'plain'
                )
            )
        except IOError:
            logging.warning(
                "No TEXT template emails/send_password_reset_mail_text.html"
            )
        if not parts:
            # Fallback to simple string replace since no templates have been
            # defined.
            parts.append(
                MIMEText(
                    'To reset your account password, click: \
                        http://%(host)s%(url)s\
                            ?email=%(email)s&reset_key=%(reset_key)s' %
                        {
                            'host': self.request.host,
                            'url': self.reverse_url('reset.password'),
                            'email': user.email,
                            'reset_key': user.reset_key
                        }, 'plain'
                )
            )

        # Attach parts into message container.
        for part in parts:
            msg.attach(part)

        self.send_mail(options.email_sender, user.email, msg.as_string())

    def post(self):
        "Sends the reset key"
        form = SendPasswordResetForm(TornadoMultiDict(self))

        if form.validate():
            User = self.get_user_model()
            email = form.email.data

            # Check if email exists in database
            user = User.objects(email=email).first()

            if not user:
                self.flash(
                    _('Email entered is not registered with us'), 'error'
                )
                self.render('user/send_reset_key.html', form=form)
                return

            reset_key = ''.join(
                random.sample(string.letters + string.digits, 15)
            )
            user.reset_key = reset_key
            user.save()

            # Send him a mail with invite
            self.send_password_reset_mail(user)

            self.flash(
                _('Instructions for resetting your password have been \
                    emailed to %s' % email), 'info'
            )

            self.redirect(
                self.get_argument('next', None) or \
                self.application.reverse_url("home")
            )
            return
        else:
            return self.render('user/send_reset_key.html', form=form)


class DoPasswordResetForm(Form):
    """Password Reset Form
    """
    password = PasswordField(
        _("Password"), [
            REQUIRED_VALIDATOR,
            validators.EqualTo(
                'confirm_password', message=_('Passwords must match')
            )
        ]
    )
    confirm_password = PasswordField(
        _("Confirm Password"), [REQUIRED_VALIDATOR, ]
    )


class PasswordResetHandler(BaseHandler):
    """Password Reset
    """

    def get(self):
        "Render password reset form"
        User = self.get_user_model()
        form = DoPasswordResetForm(TornadoMultiDict(self))

        reset_key = self.get_argument('reset_key', None)
        email = self.get_argument('email', None)

        user = User.objects(email=email, reset_key=reset_key).first()

        if not reset_key or not user:
            self.flash(_('No Valid Password Reset Key found'), 'error')

            self.redirect(self.reverse_url('send.reset.key'))
            return

        return self.render(
            'user/password_reset.html', form=form, user=user
        )

    def post(self):
        "Do password reset"
        form = DoPasswordResetForm(TornadoMultiDict(self))

        reset_key = self.get_argument('reset_key', None)
        email = self.get_argument('email', None)
        User = self.get_user_model()

        user = User.objects(email=email, reset_key=reset_key).first()

        if not reset_key or not user:
            self.flash(_(
                    "Invalid user, Try again."
                ), "warning"
            )
            self.redirect(self.reverse_url('send.reset.key'))
            return

        if form.validate():
            user.set_password(form.password.data)
            user.reset_key = None
            user.save(safe=True)

            self.flash(
                _('Password has been successfully reset.'), 'info'
            )

            self.redirect(self.reverse_url('home'))
            return

        return self.render(
            'user/password_reset.html', form=form, user=user
        )
