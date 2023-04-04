import os

from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.db.backends.signals import connection_created

from lifecycle.server.users import init_user_profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    When user is created from CLI or in admin panel, we need to create Auth Subject for him
    """
    if created:
        init_user_profile(instance.username)

        if not instance.is_staff:
            instance.is_active = False
            instance.save()


def set_search_path(sender, **kwargs):
    postgres_schema = os.environ.get('POSTGRES_SCHEMA', '')
    if postgres_schema == '{CLUSTER_FQDN}':
        cluster_hostname = os.environ.get('CLUSTER_FQDN')
        racetrack_subdomain = os.environ.get('RACETRACK_SUBDOMAIN', 'racetrack')
        assert cluster_hostname, "CLUSTER_FQDN is not set"
        parts = cluster_hostname.split('.')
        if parts[0] == racetrack_subdomain:
            postgres_schema = parts[1]
        else:
            postgres_schema = parts[0]

    if postgres_schema:
        assert not postgres_schema.startswith('"'), "POSTGRES_SCHEMA should not start with '\"'"
        assert not postgres_schema.startswith("'"), "POSTGRES_SCHEMA should not start with '\''"
        conn = kwargs.get('connection')
        if conn is not None:
            cursor = conn.cursor()
            cursor.execute(f"SET search_path='{postgres_schema}'")


connection_created.connect(set_search_path)
