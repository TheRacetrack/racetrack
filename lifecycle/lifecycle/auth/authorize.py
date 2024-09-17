from collections import defaultdict

from django.db.models import Q

from racetrack_commons.auth.auth import AuthSubjectType, UnauthorizedError
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.auth.token import AuthTokenPayload
from lifecycle.django.registry import models
from lifecycle.job.models_registry import resolve_job_model
from racetrack_commons.entities.dto import JobDto, JobFamilyDto
from racetrack_client.log.logs import get_logger
from racetrack_client.log.errors import EntityNotFound

logger = get_logger(__name__)


def authorize_subject_type(
    token_payload: AuthTokenPayload,
    allowed_types: list[AuthSubjectType],
):
    allowed_type_values = [t.value for t in allowed_types]
    if token_payload.subject_type not in allowed_type_values:
        raise UnauthorizedError(
            'wrong subject type to do this operation',
            f'auth subject type "{token_payload.subject_type}" is not one of required types: {allowed_type_values}',
        )


def authorize_resource_access(
    auth_subject: models.AuthSubject,
    job_name: str,
    job_version: str,
    scope: str,
    endpoint: str | None = None,
):
    """
    Check if auth subject has permissions to access the resource
    (job, job family) within requested scope
    :param auth_subject: Auth subject model (either User, ESC or Job family)
    :param job_name: Name of the job family
    :param job_version: Exact job version or an alias ("latest" or wildcard)
    :param scope: name of allowed operation type
    :param endpoint: optional filter for the endpoint path of the Job
    :raise UnauthorizedError: If auth subject has no permissions to access the resource
    """
    try:
        job_model = resolve_job_model(job_name, job_version)
        resolved_version = job_model.version
    except EntityNotFound:
        resolved_version = ''

    if endpoint:
        if not has_endpoint_permission(auth_subject, job_name, resolved_version, endpoint, scope):
            raise UnauthorizedError(
                'no permission to do this operation',
                f'auth subject "{auth_subject}" does not have permission to access '
                f'endpoint {endpoint} at resource "{job_name} v{resolved_version}" with scope "{scope}"'
            )
    else:
        if not has_resource_permission(auth_subject, job_name, resolved_version, scope):
            raise UnauthorizedError(
                'no permission to do this operation',
                f'auth subject "{auth_subject}" does not have permission to access '
                f'resource "{job_name} v{resolved_version}" with scope "{scope}"'
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
    scope: str | None = None,
):
    if token_payload.scopes:
        if AuthScope.FULL_ACCESS.value in token_payload.scopes:
            return
        if scope not in token_payload.scopes:
            raise UnauthorizedError(
                f'no permission to do this operation, scope "{scope}" is required',
                f'internal token does not have permission with scope "{scope}"'
            )


def has_endpoint_permission(
    auth_subject: models.AuthSubject,
    job_name: str,
    job_version: str,
    endpoint: str,
    scope: str,
) -> bool:
    subject_filter = Q(auth_subject=auth_subject)
    job_name_filter = Q(job_family__name=job_name) | Q(job_family__isnull=True)
    job_version_filter = Q(job__version=job_version) | Q(job__isnull=True)
    endpoint_filter = Q(endpoint=endpoint) | Q(endpoint__isnull=True)
    resource_filter = job_name_filter & job_version_filter & endpoint_filter
    scope_filter = Q(scope=scope) | Q(scope=AuthScope.FULL_ACCESS.value)
    queryset = models.AuthResourcePermission.objects.filter(
        subject_filter & resource_filter & scope_filter
    )
    return queryset.exists()


def has_resource_permission(
    auth_subject: models.AuthSubject,
    job_name: str,
    job_version: str,
    scope: str,
) -> bool:
    subject_filter = Q(auth_subject=auth_subject)
    job_name_filter = Q(job_family__name=job_name) | Q(job_family__isnull=True)
    job_version_filter = Q(job__version=job_version) | Q(job__isnull=True)
    resource_filter = job_name_filter & job_version_filter
    scope_filter = Q(scope=scope) | Q(scope=AuthScope.FULL_ACCESS.value)
    queryset = models.AuthResourcePermission.objects.filter(
        subject_filter & resource_filter & scope_filter
    )
    return queryset.exists()


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


def list_permitted_jobs(
    auth_subject: models.AuthSubject,
    scope: str,
    all_jobs: list[JobDto],
) -> list[JobDto]:
    """
    List jobs that auth subject has permissions to access.
    Expand permissions for all resources and whole job families,
    map them to list of individual jobs from a database.
    :param auth_subject: Auth subject model (either User, ESC or Job family)
    :param scope: name of allowed operation type (see AuthScope)
    :param all_jobs: list of Jobs to check against permission rules
    :return: List of jobs that auth subject has permissions to access (with no duplicates)
    """
    subject_filter = Q(auth_subject=auth_subject)
    scope_filter = Q(scope=scope) | Q(scope=AuthScope.FULL_ACCESS.value)
    queryset = models.AuthResourcePermission.objects.filter(
        subject_filter & scope_filter
    )

    id_to_job = {f'{f.name} v{f.version}': f for f in all_jobs}
    family_to_ids = defaultdict(list)
    for job in all_jobs:
        family_to_ids[job.name].append(f'{job.name} v{job.version}')

    job_ids = set()
    for permission in queryset: 
        if permission.job_family is None and permission.job is None:
            return all_jobs

        if permission.job is not None:
            job_ids.add(f'{permission.job.name} v{permission.job.version}')

        if permission.job_family is not None:
            job_ids.update(family_to_ids[permission.job_family.name])

    return [id_to_job[fid] for fid in sorted(job_ids)]


def list_permitted_families(
    auth_subject: models.AuthSubject,
    scope: str,
    all_families: list[JobFamilyDto],
) -> list[JobFamilyDto]:
    """
    List job families that auth subject has permissions to access.
    :param auth_subject: Auth subject model (either User, ESC or Job family)
    :param scope: name of allowed operation type (see AuthScope)
    :param all_families: list of Job families to check against permission rules
    :return: List of job families that auth subject has permissions to access (without duplicates)
    """
    subject_filter = Q(auth_subject=auth_subject)
    scope_filter = Q(scope=scope) | Q(scope=AuthScope.FULL_ACCESS.value)
    queryset = models.AuthResourcePermission.objects.filter(
        subject_filter & scope_filter
    )

    name_to_family = {f.name: f for f in all_families}
    family_names = set()
    for permission in queryset:
        if permission.job_family is None and permission.job is None:
            return all_families

        if permission.job_family is not None:
            family_names.add(permission.job.name)

    return [name_to_family[name] for name in sorted(family_names)]


def grant_permission(
    auth_subject: models.AuthSubject,
    job_name: str | None,
    job_version: str | None,
    scope: str,
):
    """
    Grant permission to access the resource (job, job family) within requested scope
    :param auth_subject: Auth subject model (either User, ESC or Job family) to give access to
    :param job_name: Name of the job family
    :param job_version: Exact job version or an alias ("latest" or wildcard)
    :param scope: name of allowed operation type (see AuthScope)
    """
    subject_filter = Q(auth_subject=auth_subject)
    scope_filter = Q(scope=scope)
    if job_name and job_version:
        resource_filter = Q(job__name=job_name, job__version=job_version)
    elif job_name:
        resource_filter = Q(job_family__name=job_name, job__isnull=True)
    else:
        resource_filter = Q(job_family__isnull=True, job__isnull=True)

    queryset = models.AuthResourcePermission.objects.filter(
        subject_filter & resource_filter & scope_filter
    )
    if queryset.exists():
        logger.warning(f'Permission for {auth_subject} to {job_name} {job_version} (scope {scope}) is already granted')
        return

    if job_name and job_version:
        job_model = models.Job.objects.get(name=job_name, version=job_version)
        permission = models.AuthResourcePermission(
            auth_subject=auth_subject,
            job=job_model,
            scope=scope,
        )
        resource_description = f'job "{job_name} v{job_version}"'
    elif job_name:
        job_family_model = models.JobFamily.objects.get(name=job_name)
        permission = models.AuthResourcePermission(
            auth_subject=auth_subject,
            job_family=job_family_model,
            scope=scope,
        )
        resource_description = f'job family "{job_name}"'
    else:
        permission = models.AuthResourcePermission(
            auth_subject=auth_subject,
            scope=scope,
        )
        resource_description = 'all jobs'

    permission.save()
    logger.info(f'"{auth_subject}" has been granted permission to {resource_description} within {scope} scope')
