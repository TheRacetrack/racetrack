from __future__ import annotations
from typing import Callable, Iterable

from lifecycle.config import Config
from lifecycle.deployer.infra_target import get_infrastructure_target, list_infrastructure_targets
from lifecycle.monitor.base import LogsStreamer
from racetrack_client.log.context_error import wrap_context
from racetrack_commons.entities.dto import FatmanDto
from racetrack_commons.plugin.engine import PluginEngine


def list_cluster_fatmen(config: Config, plugin_engine: PluginEngine) -> Iterable[FatmanDto]:
    """List fatmen deployed in a cluster"""
    infrastructures = list_infrastructure_targets(plugin_engine)
    for infrastructure in infrastructures:
        yield from infrastructure.fatman_monitor.list_fatmen(config)


def check_fatman_condition(fatman: FatmanDto, on_fatman_alive: Callable, plugin_engine: PluginEngine):
    """
    Verify if deployed Fatman is really operational
    :param on_fatman_alive: handler called when Fatman is live, but not ready yet
    (server running already, but still initializing)
    """
    infrastructure = get_infrastructure_target(plugin_engine, fatman.infrastructure_target)
    infrastructure.fatman_monitor.check_fatman_condition(fatman, fatman.update_time,
                                                         on_fatman_alive, logs_on_error=True)


def read_recent_logs(fatman: FatmanDto, tail: int, plugin_engine: PluginEngine) -> str:
    """Return last output logs from a fatman"""
    with wrap_context('reading Fatman logs'):
        infrastructure = get_infrastructure_target(plugin_engine, fatman.infrastructure_target)
        return infrastructure.fatman_monitor.read_recent_logs(fatman, tail=tail)


def list_log_streamers(
    plugin_engine: PluginEngine,
) -> list[LogsStreamer]:
    infrastructures = list_infrastructure_targets(plugin_engine)
    return [infra.logs_streamer for infra in infrastructures]
