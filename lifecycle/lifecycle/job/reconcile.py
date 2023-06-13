from lifecycle.config import Config
from lifecycle.deployer.redeploy import reprovision_job
from lifecycle.job.registry import list_job_registry
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_client.log.context_error import wrap_context, ContextError
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import JobDto, JobStatus

logger = get_logger(__name__)


def reconcile_jobs(config: Config, plugin_engine: PluginEngine):
    """Redeploy jobs missing in a cluster"""
    with wrap_context('reconciling jobs'):
        for job in list_job_registry(config):
            try:
                if is_job_reconcile_eligible(job):
                    logger.info(f'reconciling lost job {job}...')
                    reprovision_job(job.name, job.version, config, plugin_engine, 'racetrack', None)

            except BaseException as e:
                log_exception(ContextError('failed to reconcile job', e))


def is_job_reconcile_eligible(job: JobDto) -> bool:
    if job.status != JobStatus.LOST.value:
        return False
    return True
