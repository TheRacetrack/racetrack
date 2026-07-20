import time
from threading import Thread

import schedule

from image_builder.config.config import Config
from image_builder.prune import prune_build_cache
from racetrack_client.log.context_error import ContextError
from racetrack_client.log.exception import log_exception


def schedule_tasks_sync(config: Config):
    schedule.every(config.build_cache_prune_interval_m).minutes.do(prune_build_cache, config=config)

    while True:
        try:
            schedule.run_pending()
        except BaseException as e:
            log_exception(ContextError('periodic task failure', e))
        time.sleep(60)


def schedule_tasks_async(config: Config):
    """Schedule tasks to be run periodically in background"""
    Thread(target=schedule_tasks_sync, args=(config,), daemon=True).start()
