from threading import Thread
import time

from lifecycle.server.metrics import metric_database_connection_failed
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from lifecycle.config import Config
from lifecycle.server.cache import LifecycleCache

logger = get_logger(__name__)


def monitor_database_status(config: Config):
    """Start background checks of database connection"""
    if config.database_status_refresh_interval:
        Thread(target=_monitor_database_status_sync, args=(config.database_status_refresh_interval,), daemon=True).start()


def _monitor_database_status_sync(refresh_interval: float):
    while True:
        try:
            LifecycleCache.db_engine().check_connection()
        except BaseException as e:
            metric_database_connection_failed.inc()
            log_exception(e)

        time.sleep(refresh_interval)
