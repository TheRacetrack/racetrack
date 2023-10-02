import os
import time
from threading import Thread
from dataclasses import dataclass

from django.conf import settings
from django.db import connection
from django.db import DatabaseError
from django.db.backends.utils import CursorWrapper

from racetrack_client.utils.shell import shell, CommandError
from racetrack_client.log.exception import log_exception
from lifecycle.config import Config


@dataclass
class DatabaseStatus:
    connected = False


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
            shell(f'pg_isready -h {host} -p {port} -U {user} -d {db_name}', print_stdout=False)

        cursor: CursorWrapper
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return True
    except CommandError:
        return False
    except DatabaseError:
        return False
    except BaseException as e:
        log_exception(e)
        return False
