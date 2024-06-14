from django.db.backends.postgresql import base

from racetrack_client.log.logs import get_logger
from lifecycle.server.db_status import database_status
from lifecycle.server.metrics import metric_database_connection_opened, metric_database_connection_closed, \
    metric_database_cursor_created, metric_database_connection_failed

logger = get_logger(__name__)


class DatabaseWrapper(base.DatabaseWrapper):
    """Subclass of django.db.backends.postgresql.base.DatabaseWrapper, measuring connection statistics"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def connect(self):
        logger.debug("DB: connect called")
        try:
            result = super().connect()
            metric_database_connection_opened.inc()
            return result
        except BaseException as e:
            metric_database_connection_failed.inc()
            database_status.connected = False
            logger.error("DB: connect FAILED")
            raise e

    def close(self):
        metric_database_connection_closed.inc()
        logger.debug("DB: close called")
        super().close()

    def create_cursor(self, name=None):
        metric_database_cursor_created.inc()
        logger.debug("DB: create_cursor called")
        return super().create_cursor(name)
