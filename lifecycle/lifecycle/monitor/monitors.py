from __future__ import annotations
from typing import Callable, Iterable

from lifecycle.config import Config
from lifecycle.monitor.base import FatmanMonitor, LogsStreamer
from lifecycle.monitor.docker.log_stream import DockerLogsStreamer
from lifecycle.monitor.docker.monitor import DockerMonitor
from lifecycle.monitor.kubernetes.log_stream import KubernetesLogsStreamer
from lifecycle.monitor.kubernetes.monitor import KubernetesMonitor
from racetrack_client.log.context_error import wrap_context
from racetrack_commons.deploy.type import DeployerType
from racetrack_commons.entities.dto import FatmanDto
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine

"""Supported fatman monitors for different platforms"""
std_fatman_monitors: dict[str, FatmanMonitor] = {
    DeployerType.DOCKER.value: DockerMonitor(),
    DeployerType.KUBERNETES.value: KubernetesMonitor(),
}

"""Supported fatman monitors for different platforms"""
std_logs_streamers: dict[str, LogsStreamer] = {
    DeployerType.DOCKER.value: DockerLogsStreamer(),
    DeployerType.KUBERNETES.value: KubernetesLogsStreamer(),
}


def _get_fatman_monitor(config: Config, plugin_engine: PluginEngine) -> FatmanMonitor:
    plugin_fatman_monitors = _gather_plugin_fatman_monitors(plugin_engine)
    if len(plugin_fatman_monitors) == 1:
        return next(iter(plugin_fatman_monitors.values()))

    all_fatman_monitors = {**std_fatman_monitors, **plugin_fatman_monitors}
    assert config.deployer in all_fatman_monitors, f'not supported fatman monitor: {config.deployer}'
    return all_fatman_monitors[config.deployer]


def list_cluster_fatmen(config: Config, plugin_engine: PluginEngine) -> Iterable[FatmanDto]:
    """List fatmen deployed in a cluster"""
    return _get_fatman_monitor(config, plugin_engine).list_fatmen(config)


def check_fatman_condition(fatman: FatmanDto, config: Config, on_fatman_alive: Callable, plugin_engine: PluginEngine):
    """
    Verify if deployed Fatman is really operational
    :param on_fatman_alive: handler called when Fatman is live, but not ready yet
    (server running already, but still initializing)
    """
    monitor = _get_fatman_monitor(config, plugin_engine)
    monitor.check_fatman_condition(fatman, fatman.update_time,
                                   on_fatman_alive, logs_on_error=True)


def read_recent_logs(fatman: FatmanDto, tail: int, config: Config, plugin_engine: PluginEngine) -> str:
    """Return last output logs from a fatman"""
    with wrap_context('reading Fatman logs'):
        return _get_fatman_monitor(config, plugin_engine).read_recent_logs(fatman, tail=tail)


def get_logs_streamer(config: Config, plugin_engine: PluginEngine) -> LogsStreamer:
    plugin_logs_streamers = _gather_plugin_fatman_logs_streamers(plugin_engine)
    if len(plugin_logs_streamers) == 1:
        return next(iter(plugin_logs_streamers.values()))

    all_logs_streamers = {**std_logs_streamers, **plugin_logs_streamers}
    assert config.deployer in all_logs_streamers, f'not supported logs streamer: {config.deployer}'
    return all_logs_streamers[config.deployer]


def _gather_plugin_fatman_monitors(
    plugin_engine: PluginEngine,
) -> dict[str, FatmanMonitor]:
    fatman_monitors = {}

    plugin_results = plugin_engine.invoke_plugin_hook(PluginCore.fatman_monitors)
    for plugin_monitors in plugin_results:
        for deployer_name, monitor in plugin_monitors.items():
            fatman_monitors[deployer_name] = monitor

    return fatman_monitors


def _gather_plugin_fatman_logs_streamers(
    plugin_engine: PluginEngine,
) -> dict[str, LogsStreamer]:
    logs_streamers = {}

    plugin_results = plugin_engine.invoke_plugin_hook(PluginCore.fatman_logs_streamers)
    for plugin_logs_streamers in plugin_results:
        for deployer_name, logs_streamer in plugin_logs_streamers.items():
            logs_streamers[deployer_name] = logs_streamer

    return logs_streamers
