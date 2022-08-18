from typing import Tuple

from racetrack_client.log.logs import configure_logs, get_logger, init_logs
from racetrack_client.utils.config import load_config
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.config import Config
from lifecycle.server.api import run_api_server
from lifecycle.server.scheduler import schedule_tasks_sync
from lifecycle.server.supervisor import startup_check
from lifecycle.telemetry.otlp import setup_opentelemetry


logger = get_logger(__name__)


def run_lifecycle_server():
    """Serve API for deploying fatman from workspaces on demand"""
    config, plugin_engine = _init_lifecycle()
    run_api_server(config, plugin_engine)


def run_lifecycle_supervisor():
    """
    Run Lifecycle Supervisor process monitoring fatmen and scheduling tasks in background
    """
    config, plugin_engine = _init_lifecycle()
    logger.info("Starting Lifecycle Supervisor")
    startup_check()
    schedule_tasks_sync(config, plugin_engine)


def _init_lifecycle() -> Tuple[Config, PluginEngine]:
    init_logs()
    config: Config = load_config(Config)
    configure_logs(log_level=config.log_level)

    if config.open_telemetry_enabled:
        setup_opentelemetry(config)

    plugin_engine = PluginEngine(config.plugins)
    return config, plugin_engine
