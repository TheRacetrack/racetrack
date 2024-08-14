import json
import time

from django.db.utils import IntegrityError
from lifecycle.database.base_engine import NoRowsAffected
from lifecycle.database.condition_builder import QueryCondition
from lifecycle.database.table_model import new_uuid
from lifecycle.server.cache import LifecycleCache
import yaml

from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.manifest.load import load_manifest_from_dict
from racetrack_client.manifest.validate import validate_manifest
from racetrack_client.utils.time import days_ago, now, timestamp_to_datetime
from racetrack_client.utils.semver import SemanticVersion, SemanticVersionPattern
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import JobDto, JobFamilyDto, JobStatus
from lifecycle.server.metrics import metric_job_model_fetch_duration
from lifecycle.database.schema import tables

logger = get_logger(__name__)


def list_job_models() -> list[tables.Job]:
    """List deployed jobs stored in registry database"""
    mapper = LifecycleCache.record_mapper()
    return mapper.list_all(tables.Job, order_by=['-update_time', 'name'])


def list_job_family_models() -> list[tables.JobFamily]:
    """List deployed job families stored in registry database"""
    mapper = LifecycleCache.record_mapper()
    return mapper.list_all(tables.JobFamily, order_by=['name'])


def read_job_model(job_name: str, job_version: str) -> tables.Job:
    mapper = LifecycleCache.record_mapper()
    return mapper.find_one(tables.Job, name=job_name, version=job_version)


def job_exists(job_name: str, job_version: str) -> bool:
    mapper = LifecycleCache.record_mapper()
    return mapper.exists(tables.Job, name=job_name, version=job_version)


def job_family_exists(job_name: str) -> bool:
    mapper = LifecycleCache.record_mapper()
    return mapper.exists(tables.JobFamily, name=job_name)


def resolve_job_model(job_name: str, job_version: str) -> tables.Job:
    """
    Find job by name and version, accepting version aliases
    :param job_name: Name of job family
    :param job_version: Exact job version or an alias ("latest" or wildcard)
    :return: Job database model
    """
    start_time = time.time()
    try:
        if job_version == 'latest':
            return read_latest_job_model(job_name)
        elif SemanticVersionPattern.is_x_pattern(job_version):
            return read_latest_wildcard_job_model(job_name, job_version)
        else:
            return read_job_model(job_name, job_version)
    finally:
        metric_job_model_fetch_duration.observe(time.time() - start_time)


def read_latest_job_model(job_name: str) -> tables.Job:
    mapper = LifecycleCache.record_mapper()
    placeholder: str = mapper.placeholder
    filter_condition = QueryCondition(
        f'"name" = {placeholder} and "status" in ({placeholder}, {placeholder}, {placeholder})',
        job_name, JobStatus.RUNNING.value, JobStatus.ERROR.value, JobStatus.LOST.value,
    )
    jobs: list[tables.Job] = mapper.filter(tables.Job, condition=filter_condition)
    if len(jobs) == 0:
        raise EntityNotFound(f'No job named {job_name}')

    latest_job = SemanticVersion.find_latest_stable(jobs, key=lambda f: f.version)
    if latest_job is None:
        raise EntityNotFound("No stable version found")
    return latest_job


def read_latest_wildcard_job_model(job_name: str, version_wildcard: str) -> tables.Job:
    """
    :param job_name: Name of job family
    :param version_wildcard: version pattern containing "x" wildcards, e.g. "1.2.x", "2.x"
    """
    version_pattern = SemanticVersionPattern.from_x_pattern(version_wildcard)

    mapper = LifecycleCache.record_mapper()
    placeholder: str = mapper.placeholder
    filter_condition = QueryCondition(
        f'"name" = {placeholder} and "status" in ({placeholder}, {placeholder}, {placeholder})',
        job_name, JobStatus.RUNNING.value, JobStatus.ERROR.value, JobStatus.LOST.value,
    )
    jobs: list[tables.Job] = mapper.filter(tables.Job, condition=filter_condition)
    if len(jobs) == 0:
        raise EntityNotFound(f'No job named {job_name}')

    latest_job = SemanticVersion.find_latest_wildcard(version_pattern, jobs, key=lambda f: f.version)
    if latest_job is None:
        raise EntityNotFound(f"Not found any stable version matching pattern: {version_wildcard}")
    return latest_job


def read_job_family_model(job_family: str) -> tables.JobFamily:
    try:
        return LifecycleCache.record_mapper().find_one(tables.JobFamily, name=job_family)
    except EntityNotFound:
        raise EntityNotFound(f'Job Family with name {job_family} was not found')


def delete_job_model(job_name: str, job_version: str):
    mapper = LifecycleCache.record_mapper()
    job = mapper.find_one(tables.Job, name=job_name, version=job_version)
    mapper.delete_record(job)


def create_job_model(job_dto: JobDto) -> tables.Job:
    job_family = create_job_family_if_not_exist(job_dto.name)
    new_job = tables.Job(
        id=new_uuid(),
        family_id=job_family.id,
        name=job_dto.name,
        version=job_dto.version,
        status=job_dto.status,
        create_time=timestamp_to_datetime(job_dto.create_time),
        update_time=timestamp_to_datetime(job_dto.update_time),
        manifest=job_dto.manifest_yaml,
        internal_name=job_dto.internal_name,
        error=job_dto.error,
        notice=None,
        image_tag=job_dto.image_tag,
        deployed_by=job_dto.deployed_by,
        last_call_time=None,
        infrastructure_target=job_dto.infrastructure_target,
        replica_internal_names=','.join(job_dto.replica_internal_names),
        job_type_version=job_dto.job_type_version,
        infrastructure_stats=json.dumps(job_dto.infrastructure_stats),
    )
    LifecycleCache.record_mapper().create(new_job)
    return new_job


def create_job_family_model(job_family_dto: JobFamilyDto) -> tables.JobFamily:
    mapper = LifecycleCache.record_mapper()
    new_model = tables.JobFamily(
        id=new_uuid(),
        name=job_family_dto.name,
    )
    mapper.create(new_model)
    return new_model


def update_job_model(job: tables.Job, job_dto: JobDto):
    job.status = job_dto.status
    job.update_time = timestamp_to_datetime(job_dto.update_time)
    job.manifest = job_dto.manifest_yaml
    job.internal_name = job_dto.internal_name
    job.error = job_dto.error
    job.notice = job_dto.notice
    job.image_tag = job_dto.image_tag
    job.deployed_by = job_dto.deployed_by
    job.last_call_time = timestamp_to_datetime(job_dto.last_call_time) if job_dto.last_call_time is not None else None
    job.infrastructure_target = job_dto.infrastructure_target
    job.replica_internal_names = ','.join(job_dto.replica_internal_names)
    job.job_type_version = job_dto.job_type_version
    job.infrastructure_stats = json.dumps(job_dto.infrastructure_stats)
    try:
        LifecycleCache.record_mapper().update(job)
    except NoRowsAffected:
        raise EntityNotFound(f'Job model has gone before updating: {job}')


def update_job_manifest(job_name: str, job_version: str, manifest_yaml: str):
    with wrap_context('parsing YAML'):
        manifest_dict = yaml.safe_load(manifest_yaml)

    with wrap_context('manifest validation'):
        manifest = load_manifest_from_dict(manifest_dict)
        validate_manifest(manifest)
        assert manifest.name == job_name, 'job name cannot be changed'
        assert manifest.version == job_version, 'job version cannot be changed'

    job_model = read_job_model(job_name, job_version)
    job_model.manifest = manifest_yaml
    try:
        LifecycleCache.record_mapper().update(job_model)
    except NoRowsAffected:
        raise EntityNotFound(f'Job model has gone before updating: {job_model}')


def save_job_model(job_dto: JobDto) -> tables.Job:
    """Create or update existing job"""
    try:
        job_model = read_job_model(job_dto.name, job_dto.version)
    except EntityNotFound:
        return create_job_model(job_dto)
    update_job_model(job_model, job_dto)
    return job_model


def update_job(job_dto: JobDto) -> tables.Job:
    """Update existing job"""
    job_model = read_job_model(job_dto.name, job_dto.version)
    update_job_model(job_model, job_dto)
    return job_model


def create_job_family_if_not_exist(job_family: str) -> tables.JobFamily:
    try:
        return read_job_family_model(job_family)
    except EntityNotFound:
        return create_job_family_model(JobFamilyDto(name=job_family))


def create_trashed_job(job_dto: JobDto):
    age_days = days_ago(job_dto.create_time) or 0
    new_job = tables.TrashJob(
        id=job_dto.id,
        name=job_dto.name,
        version=job_dto.version,
        status=job_dto.status,
        create_time=timestamp_to_datetime(job_dto.create_time),
        update_time=timestamp_to_datetime(job_dto.update_time),
        delete_time=now(),
        manifest=job_dto.manifest_yaml,
        internal_name=job_dto.internal_name,
        error=job_dto.error,
        image_tag=job_dto.image_tag,
        deployed_by=job_dto.deployed_by,
        last_call_time=timestamp_to_datetime(job_dto.last_call_time) if job_dto.last_call_time is not None else None,
        infrastructure_target=job_dto.infrastructure_target,
        age_days=age_days,
    )
    try:
        LifecycleCache.record_mapper().create(new_job)
    except IntegrityError:
        logger.error(f'Trash Job already exists with ID={job_dto.id}, {job_dto.name} {job_dto.version}')


def find_deleted_job(
    job_name: str,
    job_version: str,
) -> tables.TrashJob | None:
    records = LifecycleCache.record_mapper().find_many(
        tables.TrashJob, name=job_name, version=job_version,
    )
    if len(records) == 0:
        return None
    return records[0]
