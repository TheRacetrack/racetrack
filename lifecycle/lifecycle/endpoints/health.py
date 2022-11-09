import os

from django.conf import settings
from django.db import connection, close_old_connections
from django.db.utils import OperationalError
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from racetrack_client.utils.shell import shell, CommandError
from lifecycle.django.registry.database import db_access
from lifecycle.config import Config


def setup_health_endpoint(api: FastAPI, config: Config):

    @api.get("/live", tags=['root'])
    async def _live():
        """Report service liveness: whether it has started"""
        return {
            'service': 'lifecycle',
            'live': True,
        }

    @api.get("/ready", tags=['root'])
    async def _ready():
        """Report service readiness: whether it's available for accepting traffic"""
        return {
            'service': 'lifecycle',
            'ready': True,
        }

    @api.get("/health", tags=['root'])
    def _health():
        """Report current application status"""
        db_connected = is_database_connected()
        status_code = 200 if db_connected else 500
        content = {
            'service': 'lifecycle',
            'live': True,
            'ready': db_connected,
            'database_connected': db_connected,
            'git_version': os.environ.get('GIT_VERSION', 'dev'),
            'docker_tag': os.environ.get('DOCKER_TAG', ''),
            'auth_required': config.auth_required,
        }
        return JSONResponse(content=content, status_code=status_code)


@db_access
def is_database_connected() -> bool:
    try:
        DJANGO_DB_TYPE = os.environ.get('DJANGO_DB_TYPE', 'sqlite')
        if DJANGO_DB_TYPE == 'postgres':
            db_name = settings.DATABASES['default']['NAME']
            user = settings.DATABASES['default']['USER']
            host = settings.DATABASES['default']['HOST']
            port = settings.DATABASES['default']['PORT']
            shell(f'pg_isready -h {host} -p {port} -U {user} -d {db_name}', print_stdout=False)

        close_old_connections()
        connection.cursor().execute("select 1")
        return True
    except CommandError:
        return False
    except OperationalError:
        return False
