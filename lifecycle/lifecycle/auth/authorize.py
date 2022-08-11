from typing import List, Optional
from collections import defaultdict

from django.db.models import Q

from racetrack_commons.auth.auth import AuthSubjectType, UnauthorizedError
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.auth.token import AuthTokenPayload
from lifecycle.django.registry import models
from lifecycle.django.registry.database import db_access
from lifecycle.fatman.models_registry import resolve_fatman_model
from racetrack_commons.entities.dto import FatmanDto, FatmanFamilyDto
from racetrack_client.log.logs import get_logger
from racetrack_client.log.errors import EntityNotFound

logger = get_logger(__name__)


def authorize_subject_type(
    token_payload: AuthTokenPayload,
    allowed_types: List[AuthSubjectType],
):
    allowed_type_values = [t.value for t in allowed_types]
    if token_payload.subject_type not in allowed_type_values:
        raise UnauthorizedError(
            'wrong subject type to do this operation',
            f'auth subject type "{token_payload.subject_type}" is not one of required types: {allowed_type_values}',
        )


def authorize_resource_access(
    auth_subject: models.AuthSubject,
    fatman_name: str,
    fatman_version: str,
    scope: str,
):
    """
    Check if auth subject has permissions to access the resource
    (fatman, fatman family) within requested scope
    :param fatman_version: Exact fatman version or an alias ("latest" or wildcard)
    :raise UnauthorizedError: If auth subject has no permissions to access the resource
    """
    try:
        fatman_model = resolve_fatman_model(fatman_name, fatman_version)
        resolved_version = fatman_model.version
    except EntityNotFound:
        resolved_version = ''

    if not has_resource_permission(auth_subject, fatman_name, resolved_version, scope):
        raise UnauthorizedError(
            'no permission to do this operation',
            f'auth subject "{auth_subject}" does not have permission to access '
            f'resource "{fatman_name} v{resolved_version}" with scope "{scope}"'
        )


def authorize_scope_access(
    auth_subject: models.AuthSubject,
    scope: str,
):
    """
    Check if auth subject has required scope permissions
    :raise UnauthorizedError: If auth subject doesn't have required permission
    """
    if not has_scope_permission(auth_subject, scope):
        raise UnauthorizedError(
            f'permission scope "{scope}" is required to do this operation',
            f'auth subject "{auth_subject}" does not have permission with scope "{scope}"'
        )


def authorize_internal_token(
    token_payload: AuthTokenPayload,
    scope: Optional[str] = None,
    fatman_name: Optional[str] = None,
    fatman_version: Optional[str] = None,
):
    if token_payload.scopes:
        if AuthScope.FULL_ACCESS.value in token_payload.scopes:
            return
        if scope not in token_payload.scopes:
            raise UnauthorizedError(
                f'no permission to do this operation, scope "{scope}" is required',
                f'internal token does not have permission with scope "{scope}"'
            )


@db_access
def has_resource_permission(
    auth_subject: models.AuthSubject,
    fatman_name: str,
    fatman_version: str,
    scope: str,
) -> bool:
    subject_filter = Q(auth_subject=auth_subject)
    resource_filter = Q(all_resources=True) | Q(fatman_family__name=fatman_name) \
        | Q(fatman__name=fatman_name, fatman__version=fatman_version)
    scope_filter = Q(scope=scope) | Q(scope=AuthScope.FULL_ACCESS.value)
    queryset = models.AuthResourcePermission.objects.filter(
        subject_filter & resource_filter & scope_filter
    )
    return queryset.exists()


@db_access
def has_scope_permission(
    auth_subject: models.AuthSubject,
    scope: str,
) -> bool:
    subject_filter = Q(auth_subject=auth_subject)
    scope_filter = Q(scope=scope) | Q(scope=AuthScope.FULL_ACCESS.value)
    queryset = models.AuthResourcePermission.objects.filter(
        subject_filter & scope_filter
    )
    return queryset.exists()


@db_access
def list_permitted_fatmen(
    auth_subject: models.AuthSubject,
    scope: str,
    all_fatmen: List[FatmanDto],
) -> List[FatmanDto]:
    """
    List fatmen that auth subject has permissions to access.
    Expand all_resources and `all_resources` and `fatman_family` fields,
    map them to list of individual fatmen from a database.
    :param scope: Scope of the access (see AuthScope)
    :return: List of fatmen that auth subject has permissions to access (with no duplicates)
    """
    subject_filter = Q(auth_subject=auth_subject)
    scope_filter = Q(scope=scope) | Q(scope=AuthScope.FULL_ACCESS.value)
    queryset = models.AuthResourcePermission.objects.filter(
        subject_filter & scope_filter
    )

    id_to_fatman = {f'{f.name} v{f.version}': f for f in all_fatmen}
    family_to_ids = defaultdict(list)
    for fatman in all_fatmen:
        family_to_ids[fatman.name].append(f'{fatman.name} v{fatman.version}')

    fatman_ids = set()
    for permission in queryset:
        if permission.all_resources:
            return all_fatmen

        if permission.fatman is not None:
            fatman_ids.add(f'{permission.fatman.name} v{permission.fatman.version}')

        if permission.fatman_family is not None:
            fatman_ids.update(family_to_ids[permission.fatman_family.name])

    return [id_to_fatman[fid] for fid in sorted(fatman_ids)]


@db_access
def list_permitted_families(
    auth_subject: models.AuthSubject,
    scope: str,
    all_families: List[FatmanFamilyDto],
) -> List[FatmanFamilyDto]:
    """
    List fatman families that auth subject has permissions to access.
    :param scope: Scope of the access (see AuthScope)
    """
    subject_filter = Q(auth_subject=auth_subject)
    scope_filter = Q(scope=scope) | Q(scope=AuthScope.FULL_ACCESS.value)
    queryset = models.AuthResourcePermission.objects.filter(
        subject_filter & scope_filter
    )

    name_to_family = {f.name: f for f in all_families}
    family_names = set()
    for permission in queryset:
        if permission.all_resources:
            return all_families

        if permission.fatman_family is not None:
            family_names.add(permission.fatman.name)

    return [name_to_family[name] for name in sorted(family_names)]


@db_access
def grant_permission(
    auth_subject: models.AuthSubject,
    fatman_name: Optional[str],
    fatman_version: Optional[str],
    scope: str,
):
    """
    Grant permission to access the resource (fatman, fatman family) within requested scope
    :param fatman_version: Exact fatman version or an alias ("latest" or wildcard)
    """
    subject_filter = Q(auth_subject=auth_subject)
    scope_filter = Q(scope=scope)
    if fatman_name and fatman_version:
        resource_filter = Q(fatman__name=fatman_name, fatman__version=fatman_version)
    elif fatman_name:
        resource_filter = Q(fatman_family__name=fatman_name)
    else:
        resource_filter = Q(all_resources=True)

    queryset = models.AuthResourcePermission.objects.filter(
        subject_filter & resource_filter & scope_filter
    )
    if queryset.exists():
        logger.warning(f'Permission for {auth_subject} to {fatman_name} {fatman_version} (scope {scope}) is already granted')
        return

    if fatman_name and fatman_version:
        fatman_model = models.Fatman.objects.get(name=fatman_name, version=fatman_version)
        permission = models.AuthResourcePermission(
            auth_subject=auth_subject,
            fatman=fatman_model,
            scope=scope,
        )
        resource_description = f'fatman "{fatman_name} v{fatman_version}"'
    elif fatman_name:
        fatman_family_model = models.FatmanFamily.objects.get(name=fatman_name)
        permission = models.AuthResourcePermission(
            auth_subject=auth_subject,
            fatman_family=fatman_family_model,
            scope=scope,
        )
        resource_description = f'fatman family "{fatman_name}"'
    else:
        permission = models.AuthResourcePermission(
            auth_subject=auth_subject,
            all_resources=True,
            scope=scope,
        )
        resource_description = 'all fatmen'

    permission.save()
    logger.info(f'"{auth_subject}" has been granted permission to {resource_description} within {scope} scope')
