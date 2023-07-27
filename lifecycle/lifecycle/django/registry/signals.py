import os

from django.db.backends.signals import connection_created


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
