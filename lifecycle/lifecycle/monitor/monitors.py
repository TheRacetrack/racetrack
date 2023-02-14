from __future__ import annotations
from typing import Callable, Iterable

from lifecycle.config import Config
from lifecycle.deployer.infra_target import get_infrastructure_target, list_infrastructure_targets
from lifecycle.monitor.base import LogsStreamer
from racetrack_client.log.context_error import wrap_context
from racetrack_commons.entities.dto import JobDto
from racetrack_commons.plugin.engine import PluginEngine


def list_cluster_jobs(config: Config, plugin_engine: PluginEngine) -> Iterable[JobDto]:
    """List jobs deployed in a cluster"""
    infrastructures = list_infrastructure_targets(plugin_engine)
    for infrastructure in infrastructures:
        yield from infrastructure.job_monitor.list_jobs(config)


def check_job_condition(job: JobDto, on_job_alive: Callable, plugin_engine: PluginEngine):
    """
    Verify if deployed Job is really operational
    :param on_job_alive: handler called when Job is live, but not ready yet
    (server running already, but still initializing)
    """
    infrastructure = get_infrastructure_target(plugin_engine, job.infrastructure_target)
    infrastructure.job_monitor.check_job_condition(job, job.update_time,
                                                         on_job_alive, logs_on_error=True)


def read_recent_logs(job: JobDto, tail: int, plugin_engine: PluginEngine) -> str:
    """Return last output logs from a job"""
    with wrap_context('reading Job logs'):
        infrastructure = get_infrastructure_target(plugin_engine, job.infrastructure_target)
        return infrastructure.job_monitor.read_recent_logs(job, tail=tail)


def list_log_streamers(
    plugin_engine: PluginEngine,
) -> list[LogsStreamer]:
    infrastructures = list_infrastructure_targets(plugin_engine)
    return [infra.logs_streamer for infra in infrastructures]
