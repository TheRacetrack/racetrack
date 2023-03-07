import time
from threading import Thread

import schedule

from lifecycle.config import Config
from lifecycle.job.registry import sync_registry_jobs
from lifecycle.job.reconcile import reconcile_jobs
from lifecycle.supervisor.metrics import populate_metrics_jobs
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_client.log.context_error import ContextError
from racetrack_client.log.exception import log_exception


def schedule_tasks_async(config: Config, plugin_engine: PluginEngine):
    Thread(target=schedule_tasks_sync, args=(config, plugin_engine), daemon=True).start()


def schedule_tasks_sync(config: Config, plugin_engine: PluginEngine):
    _schedule_tasks(config, plugin_engine)
    _scheduler_worker()


def _schedule_tasks(config: Config, plugin_engine: PluginEngine):
    schedule.every(1).minutes.do(sync_registry_jobs, config=config, plugin_engine=plugin_engine)
    schedule.every(10).minutes.do(reconcile_jobs, config=config, plugin_engine=plugin_engine)
    schedule.every(1).minutes.do(populate_metrics_jobs, config=config)


def _scheduler_worker():
    while True:
        try:
            schedule.run_pending()
        except BaseException as e:
            log_exception(ContextError('periodic task failure', e))
        time.sleep(60)  # least period of all tasks
