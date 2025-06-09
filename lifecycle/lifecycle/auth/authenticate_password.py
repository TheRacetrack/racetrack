"""
This file reimplements password authentication logic from Django==4.2.17
See site-packages/django/contrib/auth/__init__.py
"""
import inspect
import sys
from importlib import import_module
from django.db import models
# from django.contrib.auth.models import User
from lifecycle.database.schema.tables import User
from lifecycle.server.cache import LifecycleCache
from racetrack_client.log.errors import EntityNotFound

from lifecycle.auth.hasher import get_hasher, get_random_string, make_password

SESSION_KEY = "_auth_user_id"
BACKEND_SESSION_KEY = "_auth_user_backend"
HASH_SESSION_KEY = "_auth_user_hash"
REDIRECT_FIELD_NAME = "next"

AUTH_USER_MODEL = "auth.User"

UNUSABLE_PASSWORD_PREFIX = "!"  # This will never be a valid encoded hash
UNUSABLE_PASSWORD_SUFFIX_LENGTH = (
    40  # number of random chars to add after UNUSABLE_PASSWORD_PREFIX
)


def authenticate(username=None, password=None):
    """
    If the given credentials are valid, return a User object.
    """
    try:
        user = authenticate_user(username, password)
    except PermissionDenied:
        return None

    return user

def authenticate_user(username=None, password=None):
        if username is None or password is None:
            return
        try:
            user: User = LifecycleCache.record_mapper().find_one(User, username=username)
        except EntityNotFound:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).

            make_password(password)
        else:
            def setter(raw_password):
                user.password = make_password(raw_password)
                LifecycleCache.record_mapper().update(user)

            if check_password(password, user.password, setter) and user.is_active:
                return user


class PermissionDenied(Exception):
    """The user did not have permission to do that"""
    pass

class AbstractBaseUser:
    is_active = True

    REQUIRED_FIELDS = []

    # Stores the raw password if set_password() is called so that it can
    # be passed to password_changed() after the model is saved.
    _password = None

    def __str__(self):
        return self.get_username()

    def get_username(self):
        """Return the username for this User."""
        return getattr(self, self.USERNAME_FIELD)

    def clean(self):
        setattr(self, self.USERNAME_FIELD, self.normalize_username(self.get_username()))

    def natural_key(self):
        return (self.get_username(),)

    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self._password = raw_password

    def check_password(self, raw_password):
        """
        Return a boolean of whether the raw_password was correct. Handles
        hashing formats behind the scenes.
        """

        def setter(raw_password):
            self.set_password(raw_password)
            # Password hash upgrades shouldn't be considered password changes.
            self._password = None
            self.save(update_fields=["password"])

        return check_password(raw_password, self.password, setter)

    def set_unusable_password(self):
        # Set a value that will never be a valid hash
        self.password = make_password(None)

    def has_usable_password(self):
        """
        Return False if set_unusable_password() has been called for this user.
        """
        return is_password_usable(self.password)

    def get_session_auth_hash(self):
        """
        Return an HMAC of the password field.
        """
        return self._get_session_auth_hash()

    def get_session_auth_fallback_hash(self):
        for fallback_secret in settings.SECRET_KEY_FALLBACKS:
            yield self._get_session_auth_hash(secret=fallback_secret)

    def _get_session_auth_hash(self, secret=None):
        key_salt = "django.contrib.auth.models.AbstractBaseUser.get_session_auth_hash"
        return salted_hmac(
            key_salt,
            self.password,
            secret=secret,
            algorithm="sha256",
        ).hexdigest()


UserModel = AbstractBaseUser



def check_password(password, encoded, setter=None, preferred="default"):
    """
    Return a boolean of whether the raw password matches the three
    part encoded digest.

    If setter is specified, it'll be called when you need to
    regenerate the password.
    """
    fake_runtime = password is None or not is_password_usable(encoded)

    preferred = get_hasher(preferred)
    try:
        hasher = identify_hasher(encoded)
    except ValueError:
        # encoded is gibberish or uses a hasher that's no longer installed.
        fake_runtime = True

    if fake_runtime:
        # Run the default password hasher once to reduce the timing difference
        # between an existing user with an unusable password and a nonexistent
        # user or missing hasher (similar to #20760).
        make_password(get_random_string(UNUSABLE_PASSWORD_SUFFIX_LENGTH))
        return False

    hasher_changed = hasher.algorithm != preferred.algorithm
    must_update = hasher_changed or preferred.must_update(encoded)
    is_correct = hasher.verify(password, encoded)

    # If the hasher didn't change (we don't protect against enumeration if it
    # does) and the password should get updated, try to close the timing gap
    # between the work factor of the current encoded password and the default
    # work factor.
    if not is_correct and not hasher_changed and must_update:
        hasher.harden_runtime(password, encoded)

    if setter and is_correct and must_update:
        setter(password)
    return is_correct


def is_password_usable(encoded):
    """
    Return True if this password wasn't generated by
    User.set_unusable_password(), i.e. make_password(None).
    """
    return encoded is None or not encoded.startswith(UNUSABLE_PASSWORD_PREFIX)


def identify_hasher(encoded):
    """
    Return an instance of a loaded password hasher.

    Identify hasher algorithm by examining encoded hash, and call
    get_hasher() to return hasher. Raise ValueError if
    algorithm cannot be identified, or if hasher is not loaded.
    """
    # Ancient versions of Django created plain MD5 passwords and accepted
    # MD5 passwords with an empty salt.
    if (len(encoded) == 32 and "$" not in encoded) or (
        len(encoded) == 37 and encoded.startswith("md5$$")
    ):
        algorithm = "unsalted_md5"
    # Ancient versions of Django accepted SHA1 passwords with an empty salt.
    elif len(encoded) == 46 and encoded.startswith("sha1$$"):
        algorithm = "unsalted_sha1"
    else:
        algorithm = encoded.split("$", 1)[0]
    return get_hasher()
