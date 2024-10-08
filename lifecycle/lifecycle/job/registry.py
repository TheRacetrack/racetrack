from typing import Iterable
from collections import defaultdict
from lifecycle.auth.authorize import list_permitted_families, list_permitted_jobs

from lifecycle.config import Config
from lifecycle.database.schema import tables
from lifecycle.deployer.deployers import get_job_deployer
from lifecycle.job import models_registry
from lifecycle.job.audit import AuditLogger
from lifecycle.database.schema.dto_converter import job_family_record_to_dto, job_record_to_dto
from lifecycle.monitor.monitors import list_infrastructure_jobs
from lifecycle.server.cache import LifecycleCache
from lifecycle.server.metrics import metric_jobs_count_by_status
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import get_logger
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.deploy.resource import job_resource_name
from racetrack_commons.entities.audit import AuditLogEventType
from racetrack_commons.entities.dto import JobDto, JobFamilyDto, JobStatus
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine

logger = get_logger(__name__)


def list_job_registry(config: Config, auth_subject: tables.AuthSubject | None = None) -> list[JobDto]:
    """List jobs getting results from registry (Database)"""
    if auth_subject is None:
        return [job_record_to_dto(job, config) for job in models_registry.list_job_models()]
    else:
        jobs = [job_record_to_dto(job, config) for job in models_registry.list_job_models()]
        return list_permitted_jobs(auth_subject, AuthScope.READ_JOB.value, jobs)


def list_job_families(auth_subject: tables.AuthSubject | None = None) -> list[JobFamilyDto]:
    """List jobs getting results from registry (Database)"""
    if auth_subject is None:
        return [job_family_record_to_dto(family) for family in models_registry.list_job_family_models()]
    else:
        families = [job_family_record_to_dto(family) for family in models_registry.list_job_family_models()]
        return list_permitted_families(auth_subject, AuthScope.READ_JOB.value, families)


def read_job_family(job_family: str) -> JobFamilyDto:
    """Read job family from registry (Database)"""
    family_model = models_registry.read_job_family_model(job_family)
    return job_family_record_to_dto(family_model)


def read_job(job_name: str, job_version: str, config: Config) -> JobDto:
    """
    Find deployed job by name and version
    :param job_name: name of the job
    :param job_version: exact job version name
    :param config: Lifecycle configuration
    :return: deployed job as data model
    :raise EntityNotFound if job with given name doesn't exist
    """
    job_model = models_registry.read_job_model(job_name, job_version)
    return job_record_to_dto(job_model, config)


def read_versioned_job(job_name: str, job_version: str, config: Config) -> JobDto:
    """Find job by name and version, accepting version aliases"""
    job_model = models_registry.resolve_job_model(job_name, job_version)
    return job_record_to_dto(job_model, config)


def delete_job(
    job_name: str,
    job_version: str,
    config: Config,
    username: str,
    plugin_engine: PluginEngine,
):
    job = read_job(job_name, job_version, config)  # raise 404 if not found
    if job.status != JobStatus.LOST.value:
        deployer = get_job_deployer(job.infrastructure_target)
        deployer.delete_job(job_name, job_version)

    owner_username = job.deployed_by
    AuditLogger().log_event(
        AuditLogEventType.JOB_DELETED,
        username_executor=username,
        username_subject=owner_username,
        job_name=job_name,
        job_version=job_version,
    )

    models_registry.create_trashed_job(job)
    models_registry.delete_job_model(job_name, job_version)

    plugin_engine.invoke_plugin_hook(PluginCore.post_job_delete, job, username_executor=username)


def decommission_job_infrastructure(
    job_name: str,
    job_version: str,
    infrastructure_target: str,
    config: Config,
    username: str,
    plugin_engine: PluginEngine,
):
    job = read_job(job_name, job_version, config)  # raise 404 if not found
    if job.status != JobStatus.LOST.value:
        deployer = get_job_deployer(infrastructure_target)
        deployer.delete_job(job_name, job_version)

    owner_username = job.deployed_by
    AuditLogger().log_event(
        AuditLogEventType.JOB_DELETED,
        username_executor=username,
        username_subject=owner_username,
        job_name=job_name,
        job_version=job_version,
    )

    plugin_engine.invoke_plugin_hook(PluginCore.post_job_delete, job, username_executor=username)


def sync_registry_jobs(config: Config, plugin_engine: PluginEngine):
    """
    Synchronize jobs stored in the database registry and confront it with Kubernetes source of truth.
    It compares expected list of jobs with the actual state. In particular:
    - it probes every job and updates its status to RUNNING or ERROR.
    - if the job is expected to be present, but was not found in an infrastructure, it gets LOST status.
    - if there are extra jobs found in the infrastructure, called "orphans", they are ignored, but the log warning is written.
    """
    with wrap_context('synchronizing job'):
        available_job_types: set[str] = set(LifecycleCache.job_types.keys())
        infrastructure_jobs_map: dict[str, JobDto] = _generate_job_map(list_infrastructure_jobs(config, plugin_engine))
        registry_jobs_map: dict[str, JobDto] = _generate_job_map(list_job_registry(config))
        job_status_count: dict[str, int] = defaultdict(int)

        for job_id, registry_job in registry_jobs_map.items():
            if registry_job.status != JobStatus.STARTING.value:
                if job_id in infrastructure_jobs_map:
                    infrastructure_job = infrastructure_jobs_map[job_id]
                    infrastructure_job.notice = _apply_job_notice(registry_job, infrastructure_job, available_job_types)
                    _sync_registry_job(registry_job, infrastructure_job)
                else:
                    # job not present in Cluster
                    if registry_job.status != JobStatus.LOST.value:
                        logger.info(f'job is lost: {registry_job}')
                        registry_job.status = JobStatus.LOST.value
                        models_registry.update_job(registry_job)

            job_status_count[registry_job.status] += 1

        # Orphans - job missing in registry but present in infrastructure
        for job_id, infrastructure_job in infrastructure_jobs_map.items():
            if job_id not in registry_jobs_map:
                infrastructure_job.status = JobStatus.ORPHANED.value
                job_status_count[infrastructure_job.status] += 1
                logger.warning(f'orphaned job found: {infrastructure_job}, internal name: {infrastructure_job.internal_name}')

    all_jobs_count = sum(job_status_count.values())
    if job_status_count[JobStatus.RUNNING.value] != all_jobs_count:
        logger.debug(f'Jobs synchronized, count by status: {dict(job_status_count)}')
    for status in JobStatus:
        metric_jobs_count_by_status.labels(status=status.value).set(job_status_count[status.value])


def _sync_registry_job(registry_job: JobDto, infrastructure_job: JobDto):
    """
    Update database job with data taken from infrastructure.
    Do database "update" only when change is detected in order to avoid redundant database operations.
    """
    changed = False

    if registry_job.status != infrastructure_job.status:
        old_status = registry_job.status
        registry_job.status = infrastructure_job.status
        changed = True
        logger.debug(f'job {registry_job} changed status from {old_status} to {registry_job.status}')
    if registry_job.error != infrastructure_job.error:
        registry_job.error = infrastructure_job.error
        changed = True
    if registry_job.notice != infrastructure_job.notice:
        registry_job.notice = infrastructure_job.notice
        changed = True
    if registry_job.infrastructure_target != infrastructure_job.infrastructure_target:
        registry_job.infrastructure_target = infrastructure_job.infrastructure_target
        changed = True
    if registry_job.internal_name != infrastructure_job.internal_name:
        registry_job.internal_name = infrastructure_job.internal_name
        changed = True
    if registry_job.replica_internal_names != infrastructure_job.replica_internal_names:
        registry_job.replica_internal_names = infrastructure_job.replica_internal_names
        changed = True
    if registry_job.infrastructure_stats != infrastructure_job.infrastructure_stats:
        registry_job.infrastructure_stats = infrastructure_job.infrastructure_stats
        changed = True
    if infrastructure_job.last_call_time is not None:
        if registry_job.last_call_time is None or registry_job.last_call_time < infrastructure_job.last_call_time:
            registry_job.last_call_time = infrastructure_job.last_call_time
            changed = True

    if changed:
        models_registry.update_job(registry_job)


def _generate_job_map(jobs: Iterable[JobDto]) -> dict[str, JobDto]:
    return {job_resource_name(job.name, job.version): job for job in jobs}


def _apply_job_notice(registry_job: JobDto, infrastructure_job: JobDto, available_job_types: set[str]) -> str | None:
    notices: list[str] = infrastructure_job.notice.split(';') if infrastructure_job.notice else []

    if registry_job.job_type_version not in available_job_types:
        notice = "This version of the job type is obsolete and no longer available."
        if notice not in notices:
            notices.append(notice)

    return ';'.join(notices)
