from typing import Iterable, List, Optional
from lifecycle.auth.subject import get_auth_subject_by_fatman_family

from lifecycle.django.registry import models
from lifecycle.django.registry.database import db_access
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.utils.datamodel import datamodel_to_yaml_str
from racetrack_client.utils.time import days_ago, now, timestamp_to_datetime
from racetrack_client.utils.semver import SemanticVersion, SemanticVersionPattern
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import FatmanDto, FatmanFamilyDto

logger = get_logger(__name__)


@db_access
def list_fatmen_models() -> Iterable[models.Fatman]:
    """List deployed fatman stored in registry database"""
    return models.Fatman.objects.all().order_by('-update_time', 'name')


@db_access
def list_fatman_family_models() -> Iterable[models.FatmanFamily]:
    """List deployed fatman families stored in registry database"""
    return models.FatmanFamily.objects.all().order_by('name')


@db_access
def read_fatman_model(fatman_name: str, fatman_version: str) -> models.Fatman:
    try:
        return models.Fatman.objects.get(name=fatman_name, version=fatman_version)
    except models.Fatman.DoesNotExist:
        raise EntityNotFound(f'Fatman with name {fatman_name} and version {fatman_version} was not found')


def fatman_exists(fatman_name: str, fatman_version: str) -> bool:
    try:
        read_fatman_model(fatman_name, fatman_version)
        return True
    except EntityNotFound:
        return False


def fatman_family_exists(fatman_name: str) -> bool:
    try:
        read_fatman_family_model(fatman_name)
        return True
    except EntityNotFound:
        return False


def resolve_fatman_model(fatman_name: str, fatman_version: str) -> models.Fatman:
    """
    Find fatman by name and version, accepting version aliases
    :param fatman_version: Exact fatman version or an alias ("latest" or wildcard)
    :return: Fatman database model
    """
    if fatman_version == 'latest':
        return read_latest_fatman_model(fatman_name)
    elif SemanticVersionPattern.is_wildcard_pattern(fatman_version):
        return read_latest_wildcard_fatman_model(fatman_name, fatman_version)
    else:
        return read_fatman_model(fatman_name, fatman_version)


@db_access
def read_latest_fatman_model(fatman_name: str) -> models.Fatman:
    fatmen_queryset = models.Fatman.objects.filter(name=fatman_name)
    if fatmen_queryset.count() == 0:
        raise EntityNotFound(f'No fatman named {fatman_name}')
    fatmen: List[models.Fatman] = list(fatmen_queryset)

    latest_fatman = SemanticVersion.find_latest_stable(fatmen, key=lambda f: f.version)
    if latest_fatman is None:
        raise EntityNotFound("No stable version found")

    return latest_fatman


@db_access
def read_latest_wildcard_fatman_model(fatman_name: str, version_wildcard: str) -> models.Fatman:
    """
    :param version_wildcard: version pattern containing "x" wildcards, eg. "1.2.x", "2.x"
    """
    version_pattern = SemanticVersionPattern(version_wildcard)

    fatmen_queryset = models.Fatman.objects.filter(name=fatman_name)
    if fatmen_queryset.count() == 0:
        raise EntityNotFound(f'No fatman named {fatman_name}')
    fatmen: List[models.Fatman] = list(fatmen_queryset)

    latest_fatman = SemanticVersion.find_latest_wildcard(version_pattern, fatmen, key=lambda f: f.version)
    if latest_fatman is None:
        raise EntityNotFound(f"Not found any stable version matching pattern: {version_wildcard}")

    return latest_fatman


@db_access
def read_fatman_family_model(fatman_family: str) -> models.FatmanFamily:
    try:
        return models.FatmanFamily.objects.get(name=fatman_family)
    except models.FatmanFamily.DoesNotExist:
        raise EntityNotFound(f'Fatman Family with name {fatman_family} was not found')


@db_access
def delete_fatman_model(fatman_name: str, fatman_version: str):
    models.Fatman.objects.get(name=fatman_name, version=fatman_version).delete()


@db_access
def create_fatman_model(fatman_dto: FatmanDto) -> models.Fatman:
    fatman_family = create_fatman_family_if_not_exist(fatman_dto.name)
    new_fatman = models.Fatman(
        name=fatman_dto.name,
        version=fatman_dto.version,
        family=fatman_family,
        status=fatman_dto.status,
        create_time=timestamp_to_datetime(fatman_dto.create_time),
        update_time=timestamp_to_datetime(fatman_dto.update_time),
        manifest=datamodel_to_yaml_str(fatman_dto.manifest) if fatman_dto.manifest is not None else None,
        internal_name=fatman_dto.internal_name,
        error=fatman_dto.error,
        image_tag=fatman_dto.image_tag,
        deployed_by=fatman_dto.deployed_by,
        infrastructure_target=fatman_dto.infrastructure_target,
    )
    new_fatman.save()
    return new_fatman


@db_access
def create_fatman_family_model(fatman_family_dto: FatmanFamilyDto) -> models.FatmanFamily:
    new_model = models.FatmanFamily(
        name=fatman_family_dto.name,
    )
    new_model.save()
    get_auth_subject_by_fatman_family(new_model)
    return new_model


@db_access
def update_fatman_model(fatman: models.Fatman, fatman_dto: FatmanDto):
    fatman.status = fatman_dto.status
    fatman.update_time = timestamp_to_datetime(fatman_dto.update_time)
    fatman.manifest = datamodel_to_yaml_str(fatman_dto.manifest) if fatman_dto.manifest is not None else None
    fatman.internal_name = fatman_dto.internal_name
    fatman.error = fatman_dto.error
    fatman.image_tag = fatman_dto.image_tag
    fatman.deployed_by = fatman_dto.deployed_by
    fatman.last_call_time = timestamp_to_datetime(fatman_dto.last_call_time) if fatman_dto.last_call_time is not None else None
    fatman.infrastructure_target = fatman_dto.infrastructure_target
    fatman.save()


@db_access
def save_fatman_model(fatman_dto: FatmanDto) -> models.Fatman:
    """Create or update existing fatman"""
    try:
        fatman_model = read_fatman_model(fatman_dto.name, fatman_dto.version)
        update_fatman_model(fatman_model, fatman_dto)
        return fatman_model
    except EntityNotFound:
        return create_fatman_model(fatman_dto)


@db_access
def create_fatman_family_if_not_exist(fatman_family: str) -> models.FatmanFamily:
    try:
        return read_fatman_family_model(fatman_family)
    except EntityNotFound:
        return create_fatman_family_model(FatmanFamilyDto(name=fatman_family))


@db_access
def create_trashed_fatman(fatman_dto: FatmanDto) -> models.TrashFatman:
    age_days = days_ago(fatman_dto.create_time)
    new_fatman = models.TrashFatman(
        id=fatman_dto.id,
        name=fatman_dto.name,
        version=fatman_dto.version,
        status=fatman_dto.status,
        create_time=timestamp_to_datetime(fatman_dto.create_time),
        update_time=timestamp_to_datetime(fatman_dto.update_time),
        delete_time=now(),
        manifest=datamodel_to_yaml_str(fatman_dto.manifest) if fatman_dto.manifest is not None else None,
        internal_name=fatman_dto.internal_name,
        error=fatman_dto.error,
        image_tag=fatman_dto.image_tag,
        deployed_by=fatman_dto.deployed_by,
        last_call_time=timestamp_to_datetime(fatman_dto.last_call_time) if fatman_dto.last_call_time is not None else None,
        infrastructure_target=fatman_dto.infrastructure_target,
        age_days=age_days,
    )
    new_fatman.save()
    return new_fatman


@db_access
def find_deleted_fatman(
    fatman_name: str,
    fatman_version: str,
) -> Optional[models.TrashFatman]:
    queryset = models.TrashFatman.objects.filter(
        name=fatman_name, version=fatman_version,
    )
    if queryset.count() == 0:
        return None
    return queryset.first()
