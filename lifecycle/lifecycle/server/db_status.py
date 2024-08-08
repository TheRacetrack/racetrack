import os
import time
from threading import Thread
from dataclasses import dataclass

from django.conf import settings
from django.db import connection, DatabaseError, close_old_connections
from django.db.backends.utils import CursorWrapper

from racetrack_client.utils.shell import shell, CommandError
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from lifecycle.config import Config

logger = get_logger(__name__)


@dataclass
class DatabaseStatus:
    connected = True


database_status = DatabaseStatus()


def monitor_database_status(config: Config):
    """Start background checks of database connection"""
    if config.database_status_refresh_interval:
        Thread(target=_monitor_database_status_sync, args=(config.database_status_refresh_interval,), daemon=True).start()


def _monitor_database_status_sync(refresh_interval: float):
    while True:
        database_status.connected = is_database_connected()
        time.sleep(refresh_interval)


def is_database_connected() -> bool:
    try:
        django_db_type = os.environ.get('DJANGO_DB_TYPE', 'sqlite')
        if django_db_type == 'postgres':
            db_name = settings.DATABASES['default']['NAME']
            user = settings.DATABASES['default']['USER']
            host = settings.DATABASES['default']['HOST']
            port = settings.DATABASES['default']['PORT']
            shell(f'pg_isready -h {host} -p {port} -U {user} -d {db_name}', print_stdout=False, print_log=False)

        close_old_connections()
        cursor: CursorWrapper
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return True
    except CommandError:
        logger.error('Connection to database failed (pg_isready failed)')
        return False
    except DatabaseError as e:
        logger.error(f'Connection to database failed (DatabaseError): {e}')
        return False
    except BaseException as e:
        log_exception(e)
        return False
