import os
from pathlib import Path

from racetrack_commons.database.database import populate_database_settings


def test_populate_database_settings():
    try:
        os.environ['DJANGO_DB_TYPE'] = 'postgres'
        os.environ['POSTGRES_DB'] = 'racetrack-{CLUSTER_NAME}'
        os.environ['POSTGRES_USER'] = 'johny'
        os.environ['POSTGRES_PASSWORD'] = '***'
        os.environ['POSTGRES_HOST'] = 'localhost'
        os.environ['POSTGRES_PORT'] = '5432'
        os.environ['CLUSTER_FQDN'] = 'racetrack.dev-c1.cluster.example.com'
        os.environ['RACETRACK_SUBDOMAIN'] = 'racetrack'

        databases = populate_database_settings(Path('.'))
        assert databases['default'] == {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'racetrack-dev-c1',
            'USER': 'johny',
            'PASSWORD': '***',
            'HOST': 'localhost',
            'PORT': '5432',
            'CONN_MAX_AGE': 60,
        }

    finally:
        del os.environ['DJANGO_DB_TYPE']
