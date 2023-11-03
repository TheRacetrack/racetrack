from typing import Iterable, List, Optional

from django.db.utils import IntegrityError
import yaml

from lifecycle.auth.subject import get_auth_subject_by_job_family
from lifecycle.django.registry import models
from lifecycle.django.registry.database import db_access
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.manifest.load import load_manifest_from_dict
from racetrack_client.manifest.validate import validate_manifest
from racetrack_client.utils.time import days_ago, now, timestamp_to_datetime
from racetrack_client.utils.semver import SemanticVersion, SemanticVersionPattern
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import JobDto, JobFamilyDto

logger = get_logger(__name__)


@db_access
def list_job_models() -> Iterable[models.Job]:
    """List deployed jobs stored in registry database"""
    return models.Job.objects.all().order_by('-update_time', 'name')


@db_access
def list_job_family_models() -> Iterable[models.JobFamily]:
    """List deployed job families stored in registry database"""
    return models.JobFamily.objects.all().order_by('name')


@db_access
def read_job_model(job_name: str, job_version: str) -> models.Job:
    try:
        return models.Job.objects.get(name=job_name, version=job_version)
    except models.Job.DoesNotExist:
        raise EntityNotFound(f'Job with name {job_name} and version {job_version} was not found')


def job_exists(job_name: str, job_version: str) -> bool:
    try:
        read_job_model(job_name, job_version)
        return True
    except EntityNotFound:
        return False


def job_family_exists(job_name: str) -> bool:
    try:
        read_job_family_model(job_name)
        return True
    except EntityNotFound:
        return False


def resolve_job_model(job_name: str, job_version: str) -> models.Job:
    """
    Find job by name and version, accepting version aliases
    :param job_version: Exact job version or an alias ("latest" or wildcard)
    :return: Job database model
    """
    if job_version == 'latest':
        return read_latest_job_model(job_name)
    elif SemanticVersionPattern.is_x_pattern(job_version):
        return read_latest_wildcard_job_model(job_name, job_version)
    else:
        return read_job_model(job_name, job_version)


@db_access
def read_latest_job_model(job_name: str) -> models.Job:
    job_queryset = models.Job.objects.filter(name=job_name)
    if job_queryset.count() == 0:
        raise EntityNotFound(f'No job named {job_name}')
    jobs: List[models.Job] = list(job_queryset)

    latest_job = SemanticVersion.find_latest_stable(jobs, key=lambda f: f.version)
    if latest_job is None:
        raise EntityNotFound("No stable version found")

    return latest_job


@db_access
def read_latest_wildcard_job_model(job_name: str, version_wildcard: str) -> models.Job:
    """
    :param version_wildcard: version pattern containing "x" wildcards, eg. "1.2.x", "2.x"
    """
    version_pattern = SemanticVersionPattern.from_x_pattern(version_wildcard)

    job_queryset = models.Job.objects.filter(name=job_name)
    if job_queryset.count() == 0:
        raise EntityNotFound(f'No job named {job_name}')
    jobs: List[models.Job] = list(job_queryset)

    latest_job = SemanticVersion.find_latest_wildcard(version_pattern, jobs, key=lambda f: f.version)
    if latest_job is None:
        raise EntityNotFound(f"Not found any stable version matching pattern: {version_wildcard}")

    return latest_job


@db_access
def read_job_family_model(job_family: str) -> models.JobFamily:
    try:
        return models.JobFamily.objects.get(name=job_family)
    except models.JobFamily.DoesNotExist:
        raise EntityNotFound(f'Job Family with name {job_family} was not found')


@db_access
def delete_job_model(job_name: str, job_version: str):
    models.Job.objects.get(name=job_name, version=job_version).delete()


@db_access
def create_job_model(job_dto: JobDto) -> models.Job:
    job_family = create_job_family_if_not_exist(job_dto.name)
    new_job = models.Job(
        name=job_dto.name,
        version=job_dto.version,
        family=job_family,
        status=job_dto.status,
        create_time=timestamp_to_datetime(job_dto.create_time),
        update_time=timestamp_to_datetime(job_dto.update_time),
        manifest=job_dto.manifest_yaml,
        internal_name=job_dto.internal_name,
        error=job_dto.error,
        image_tag=job_dto.image_tag,
        deployed_by=job_dto.deployed_by,
        infrastructure_target=job_dto.infrastructure_target,
        replica_internal_names=','.join(job_dto.replica_internal_names),
        job_type_version=job_dto.job_type_version,
    )
    new_job.save()
    return new_job


@db_access
def create_job_family_model(job_family_dto: JobFamilyDto) -> models.JobFamily:
    new_model = models.JobFamily(
        name=job_family_dto.name,
    )
    new_model.save()
    get_auth_subject_by_job_family(new_model)
    return new_model


@db_access
def update_job_model(job: models.Job, job_dto: JobDto):
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
    job.save()


@db_access
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
    job_model.save()


@db_access
def save_job_model(job_dto: JobDto) -> models.Job:
    """Create or update existing job"""
    try:
        job_model = read_job_model(job_dto.name, job_dto.version)
        update_job_model(job_model, job_dto)
        return job_model
    except EntityNotFound:
        return create_job_model(job_dto)


@db_access
def create_job_family_if_not_exist(job_family: str) -> models.JobFamily:
    try:
        return read_job_family_model(job_family)
    except EntityNotFound:
        return create_job_family_model(JobFamilyDto(name=job_family))


@db_access
def create_trashed_job(job_dto: JobDto):
    age_days = days_ago(job_dto.create_time)
    new_job = models.TrashJob(
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
        new_job.save()
    except IntegrityError:
        logger.warning(f'Trash Job already exists with ID={job_dto.id}')


@db_access
def find_deleted_job(
    job_name: str,
    job_version: str,
) -> Optional[models.TrashJob]:
    queryset = models.TrashJob.objects.filter(
        name=job_name, version=job_version,
    )
    if queryset.count() == 0:
        return None
    return queryset.first()
