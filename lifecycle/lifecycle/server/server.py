from typing import Tuple

from lifecycle.server.db_status import monitor_database_status
from racetrack_client.log.logs import configure_logs, get_logger
from racetrack_client.utils.config import load_config
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.config import Config
from lifecycle.server.api import run_api_server
from lifecycle.server.cache import LifecycleCache
from lifecycle.supervisor.scheduler import schedule_tasks_async
from lifecycle.supervisor.startup import startup_check


logger = get_logger(__name__)


def run_lifecycle_server():
    """Serve API for deploying job from workspaces on demand"""
    config, plugin_engine = _init_lifecycle()
    monitor_database_status(config)
    run_api_server(config, plugin_engine)


def run_lifecycle_supervisor():
    """
    Run Lifecycle Supervisor process monitoring jobs and scheduling tasks in background
    """
    config, plugin_engine = _init_lifecycle()
    logger.info("Starting Lifecycle Supervisor")
    startup_check()
    schedule_tasks_async(config, plugin_engine)
    monitor_database_status(config)
    run_api_server(config, plugin_engine, 'lifecycle-supervisor')


def _init_lifecycle() -> Tuple[Config, PluginEngine]:
    configure_logs()
    config: Config = load_config(Config)
    LifecycleCache.config = config
    plugin_engine = PluginEngine(config.plugins_dir, on_reload=LifecycleCache.on_plugins_reload)
    return config, plugin_engine
