import time

import schedule
from lifecycle.config import Config
from lifecycle.fatman.registry import sync_registry_fatmen
from lifecycle.fatman.reconcile import reconcile_fatmen
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_client.log.context_error import ContextError
from racetrack_client.log.exception import log_exception


def schedule_tasks_sync(config: Config, plugin_engine: PluginEngine):
    _schedule_tasks(config, plugin_engine)
    _scheduler_worker()


def _schedule_tasks(config: Config, plugin_engine: PluginEngine):
    schedule.every(1).minutes.do(sync_registry_fatmen, config=config, plugin_engine=plugin_engine)
    schedule.every(10).minutes.do(reconcile_fatmen, config=config, plugin_engine=plugin_engine)


def _scheduler_worker():
    while True:
        try:
            schedule.run_pending()
        except BaseException as e:
            log_exception(ContextError('periodic task failure', e))
        time.sleep(60)  # least period of all tasks
