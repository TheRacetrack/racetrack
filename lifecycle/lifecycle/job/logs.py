from racetrack_client.log.errors import EntityNotFound
from lifecycle.config import Config
from lifecycle.database.schema import tables
from lifecycle.job.registry import read_versioned_job
from lifecycle.job import models_registry
from lifecycle.monitor.monitors import read_recent_logs
from lifecycle.server.cache import LifecycleCache


def read_runtime_logs(job_name: str, job_version: str, tail: int, config: Config) -> str:
    """Read recent logs from running job by its name"""
    job = read_versioned_job(job_name, job_version, config)
    return read_recent_logs(job, tail)


def read_build_logs(job_name: str, job_version: str, tail: int) -> str:
    """Read build logs from job image during latest job deployment"""
    job_model = models_registry.resolve_job_model(job_name, job_version)

    deployments = LifecycleCache.record_mapper().find_many(
        tables.Deployment,
        order_by=['-update_time'],
        job_name=job_model.name,
        job_version=job_model.version,
    )

    if not deployments:
        raise EntityNotFound(f'No deployment matching to a job {job_name}')
    latest_deployment: tables.Deployment = deployments[0]
    logs: str = latest_deployment.build_logs or ''
    if tail > 0:
        logs = '\n'.join(logs.splitlines()[-tail:])
    return logs
