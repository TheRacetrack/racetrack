from lifecycle.config import Config
from lifecycle.django.registry import models
from lifecycle.job.registry import read_versioned_job
from lifecycle.job import models_registry
from lifecycle.monitor.monitors import read_recent_logs
from racetrack_client.log.errors import EntityNotFound
from racetrack_commons.plugin.engine import PluginEngine


def read_runtime_logs(job_name: str, job_version: str, tail: int, config: Config, plugin_engine: PluginEngine) -> str:
    """Read recent logs from running job by its name"""
    job = read_versioned_job(job_name, job_version, config)
    return read_recent_logs(job, tail, plugin_engine)


def read_build_logs(job_name: str, job_version: str, tail: int) -> str:
    """Read build logs from fatman image during latest job deployment"""
    job_model = models_registry.resolve_job_model(job_name, job_version)
    deployments_queryset = models.Deployment.objects\
        .filter(job_name=job_model.name, job_version=job_model.version)\
        .order_by('-update_time')
    if deployments_queryset.count() == 0:
        raise EntityNotFound(f'No deployment matching to a job {job_name}')
    latest_deployment: models.Deployment = list(deployments_queryset)[0]
    logs: str = latest_deployment.build_logs or ''
    if tail > 0:
        logs = '\n'.join(logs.splitlines()[-tail:])
    return logs
