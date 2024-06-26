from django.db.backends.postgresql import base
from psycopg import Connection

from racetrack_client.log.logs import get_logger
from lifecycle.server.db_status import database_status
from lifecycle.server.metrics import metric_database_connection_opened, metric_database_connection_closed, \
    metric_database_cursor_created, metric_database_connection_failed

logger = get_logger(__name__)


class DatabaseWrapper(base.DatabaseWrapper):
    """Subclass of django.db.backends.postgresql.base.DatabaseWrapper, measuring connection statistics"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_new_connection(self, conn_params):
        try:
            connection: Connection = super().get_new_connection(conn_params)
            metric_database_connection_opened.inc()
            old_close = connection.close

            def new_close():
                metric_database_connection_closed.inc()
                old_close()

            connection.close = new_close
            return connection

        except BaseException as e:
            metric_database_connection_failed.inc()
            database_status.connected = False
            logger.error(f'Connection to database failed: {e}')
            raise e

    def create_cursor(self, name=None):
        metric_database_cursor_created.inc()
        return super().create_cursor(name)
