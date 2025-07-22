from typing import Callable, Iterable

from lifecycle.config import Config
from lifecycle.infrastructure.infra_target import get_infrastructure_target, list_infrastructure_targets
from lifecycle.monitor.base import LogsStreamer
from racetrack_client.log.context_error import wrap_context, ContextError
from racetrack_client.log.exception import log_exception
from racetrack_commons.entities.dto import JobDto
from racetrack_commons.plugin.engine import PluginEngine


def list_infrastructure_jobs(config: Config, plugin_engine: PluginEngine) -> Iterable[JobDto]:
    """List jobs deployed in all infrastructures"""
    infrastructures = list_infrastructure_targets(plugin_engine)
    for infrastructure in infrastructures:
        try:
            if infrastructure.job_monitor is None:
                raise ValueError("job monitor is None")

            yield from infrastructure.job_monitor.list_jobs(config)
        except BaseException as e:
            log_exception(ContextError(f'failed to list jobs from {infrastructure}', e))


def check_job_condition(job: JobDto, on_job_alive: Callable):
    """
    Verify if deployed Job is really operational
    :param job: job data
    :param on_job_alive: handler called when Job is live, but not ready yet
    (server running already, but still initializing)
    """
    infrastructure = get_infrastructure_target(job.infrastructure_target)

    if infrastructure.job_monitor is None:
                raise ValueError("job monitor is None")

    infrastructure.job_monitor.check_job_condition(job, job.update_time,
                                                   on_job_alive, logs_on_error=True)


def read_recent_logs(job: JobDto, tail: int) -> str:
    """Return last output logs from a job"""
    with wrap_context('reading Job logs'):
        infrastructure = get_infrastructure_target(job.infrastructure_target)

        if infrastructure.job_monitor is None:
                raise ValueError("job monitor is None")

        return infrastructure.job_monitor.read_recent_logs(job, tail=tail)


def list_log_streamers(
    plugin_engine: PluginEngine,
) -> list[LogsStreamer | None]:
    infrastructures = list_infrastructure_targets(plugin_engine)
    return [infra.logs_streamer for infra in infrastructures]
