import logging
import os

from django.contrib.auth import user_logged_in
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.conf import settings
from django.db.backends.signals import connection_created

from racetrack_client.utils.request import ResponseError
from racetrack_commons.entities.users_client import UserRegistryClient
from racetrack_commons.auth.token import decode_jwt
from dashboard.session import RT_SESSION_USER_AUTH_KEY


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    When regular user registers on Dashboard, we need to create an Auth Subject for him.
    This notifies Lifecycle API through http.
    """

    if created and not instance.is_staff:
        try:
            UserRegistryClient(settings.LIFECYCLE_AUTH_TOKEN).init_user_profile(instance.username)
        except ResponseError as err:
            if settings.RUNNING_ON_LOCALHOST and "User has no profile" in str(err):
                # Expected and can't do anything about it because Dashboard doesn't share db with Lifecycle
                pass
            else:
                logging.error(f"Create user profile: couldn't connect: {err}")
                raise err

        # This is helper for localhost mode, so that developer doesn't need to constantly activate user
        user_should_be_active = settings.RUNNING_ON_LOCALHOST

        instance.is_active = user_should_be_active
        instance.save()


@receiver(user_logged_in)
def on_login(sender, user, request, **kwargs):
    urc = UserRegistryClient(settings.LIFECYCLE_AUTH_TOKEN)
    profile = urc.get_user_profile(request.user.username)
    token = profile.token
    decode_jwt(token)

    # This will be later set as cookie in UserCookieMiddleWare
    request.session[RT_SESSION_USER_AUTH_KEY] = token


def set_search_path(sender, **kwargs):
    POSTGRES_SCHEMA = os.environ.get('POSTGRES_SCHEMA', '')
    if POSTGRES_SCHEMA == '{CLUSTER_FQDN}':
        cluster_hostname = os.environ.get('CLUSTER_FQDN')
        racetrack_subdomain = os.environ.get('RACETRACK_SUBDOMAIN', 'racetrack')
        assert cluster_hostname, "CLUSTER_FQDN is not set"
        parts = cluster_hostname.split('.')
        if parts[0] == racetrack_subdomain:
            POSTGRES_SCHEMA = parts[1]
        else:
            POSTGRES_SCHEMA = parts[0]

    if POSTGRES_SCHEMA:
        assert not POSTGRES_SCHEMA.startswith('"'), "POSTGRES_SCHEMA should not start with '\"'"
        assert not POSTGRES_SCHEMA.startswith("'"), "POSTGRES_SCHEMA should not start with '\''"
        conn = kwargs.get('connection')
        if conn is not None:
            cursor = conn.cursor()
            cursor.execute(f"SET search_path='{POSTGRES_SCHEMA}'")


connection_created.connect(set_search_path)
