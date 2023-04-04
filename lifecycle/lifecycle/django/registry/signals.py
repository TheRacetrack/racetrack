import os

from django.db.backends.signals import connection_created


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
