from collections import defaultdict

from lifecycle.auth.subject import get_description_from_auth_subject
from lifecycle.database.condition_builder import QueryCondition
from lifecycle.database.schema import tables
from lifecycle.database.table_model import table_name
from lifecycle.server.cache import LifecycleCache
from racetrack_commons.auth.auth import AuthSubjectType, UnauthorizedError
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.auth.token import AuthTokenPayload
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
    auth_subject: tables.AuthSubject,
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
            subject_info = get_description_from_auth_subject(auth_subject)
            raise UnauthorizedError(
                'no permission to do this operation',
                f'auth subject "{subject_info}" does not have permission to access '
                f'endpoint {endpoint} at resource "{job_name} v{resolved_version}" with scope "{scope}"'
            )
    else:
        if not has_resource_permission(auth_subject, job_name, resolved_version, scope):
            subject_info = get_description_from_auth_subject(auth_subject)
            raise UnauthorizedError(
                'no permission to do this operation',
                f'auth subject "{subject_info}" does not have permission to access '
                f'resource "{job_name} v{resolved_version}" with scope "{scope}"'
            )


def authorize_scope_access(
    auth_subject: tables.AuthSubject,
    scope: str,
):
    """
    Check if auth subject has required scope permissions
    :raise UnauthorizedError: If auth subject doesn't have required permission
    """
    if not has_scope_permission(auth_subject, scope):
        subject_info = get_description_from_auth_subject(auth_subject)
        raise UnauthorizedError(
            f'permission scope "{scope}" is required to do this operation',
            f'auth subject "{subject_info}" does not have permission with scope "{scope}"'
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
    auth_subject: tables.AuthSubject,
    job_name: str,
    job_version: str,
    endpoint: str,
    scope: str,
) -> bool:
    mapper = LifecycleCache.record_mapper()
    placeholder: str = mapper.placeholder
    table_permission = table_name(tables.AuthResourcePermission)
    table_family = table_name(tables.JobFamily)
    table_job = table_name(tables.Job)
    join_expression = f'left join {table_family} on {table_family}.id = {table_permission}.job_family_id'
    join_expression += f' left join {table_job} on {table_job}.id = {table_permission}.job_id'

    subject_filter = QueryCondition(f'{table_permission}.auth_subject_id = {placeholder}', auth_subject.id)
    job_name_filter = QueryCondition.operator_or(
        QueryCondition(f'{table_family}.name = {placeholder}', job_name),
        QueryCondition(f'{table_permission}.job_family_id is null'),
    )
    job_version_filter = QueryCondition.operator_or(
        QueryCondition(f'{table_job}.version = {placeholder}', job_version),
        QueryCondition(f'{table_permission}.job_id is null'),
    )
    endpoint_filter = QueryCondition.operator_or(
        QueryCondition(f'{table_permission}.endpoint = {placeholder}', endpoint),
        QueryCondition(f'{table_permission}.endpoint is null'),
    )
    scope_filter = QueryCondition.operator_or(
        QueryCondition(f'{table_permission}.scope = {placeholder}', scope),
        QueryCondition(f'{table_permission}.scope = {placeholder}', AuthScope.FULL_ACCESS.value),
    )
    filter_condition = QueryCondition.operator_and(
        subject_filter,
        QueryCondition.operator_and(
            job_name_filter,
            job_version_filter,
            endpoint_filter,
        ),
        scope_filter,
    )

    return mapper.exists_on_condition(
        tables.AuthResourcePermission, join_expression=join_expression, condition=filter_condition,
    )


def has_resource_permission(
    auth_subject: tables.AuthSubject,
    job_name: str,
    job_version: str,
    scope: str,
) -> bool:
    mapper = LifecycleCache.record_mapper()
    placeholder: str = mapper.placeholder
    table_permission = table_name(tables.AuthResourcePermission)
    table_family = table_name(tables.JobFamily)
    table_job = table_name(tables.Job)
    join_expression = f'left join {table_family} on {table_family}.id = {table_permission}.job_family_id'
    join_expression += f' left join {table_job} on {table_job}.id = {table_permission}.job_id'

    subject_filter = QueryCondition(f'{table_permission}.auth_subject_id = {placeholder}', auth_subject.id)
    job_name_filter = QueryCondition.operator_or(
        QueryCondition(f'{table_family}.name = {placeholder}', job_name),
        QueryCondition(f'{table_permission}.job_family_id is null'),
    )
    job_version_filter = QueryCondition.operator_or(
        QueryCondition(f'{table_job}.version = {placeholder}', job_version),
        QueryCondition(f'{table_permission}.job_id is null'),
    )
    scope_filter = QueryCondition.operator_or(
        QueryCondition(f'{table_permission}.scope = {placeholder}', scope),
        QueryCondition(f'{table_permission}.scope = {placeholder}', AuthScope.FULL_ACCESS.value),
    )
    filter_condition = QueryCondition.operator_and(
        subject_filter,
        QueryCondition.operator_and(
            job_name_filter,
            job_version_filter,
        ),
        scope_filter,
    )

    return mapper.exists_on_condition(
        tables.AuthResourcePermission, join_expression=join_expression, condition=filter_condition,
    )


def has_scope_permission(
    auth_subject: tables.AuthSubject,
    scope: str,
) -> bool:
    mapper = LifecycleCache.record_mapper()
    placeholder: str = mapper.placeholder
    table_permission = table_name(tables.AuthResourcePermission)

    subject_filter = QueryCondition(f'{table_permission}.auth_subject_id = {placeholder}', auth_subject.id)
    scope_filter = QueryCondition.operator_or(
        QueryCondition(f'{table_permission}.scope = {placeholder}', scope),
        QueryCondition(f'{table_permission}.scope = {placeholder}', AuthScope.FULL_ACCESS.value),
    )
    filter_condition = QueryCondition.operator_and(
        subject_filter,
        scope_filter,
    )

    return mapper.exists_on_condition(
        tables.AuthResourcePermission, condition=filter_condition,
    )


def list_permitted_jobs(
    auth_subject: tables.AuthSubject,
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
    mapper = LifecycleCache.record_mapper()
    placeholder: str = mapper.placeholder
    subject_filter = QueryCondition(f'auth_subject_id = {placeholder}', auth_subject.id)
    scope_filter = QueryCondition.operator_or(
        QueryCondition(f'scope = {placeholder}', scope),
        QueryCondition(f'scope = {placeholder}', AuthScope.FULL_ACCESS.value),
    )
    filter_condition = QueryCondition.operator_and(
        subject_filter,
        scope_filter,
    )
    permissions = mapper.filter(tables.AuthResourcePermission, condition=filter_condition)

    id_to_job: dict[str, JobDto] = {job.id or '': job for job in all_jobs}
    family_to_job_ids = defaultdict(list)
    for job in all_jobs:
        family_to_job_ids[job.name].append(job.id)

    job_ids = set()
    for permission in permissions: 
        if permission.job_family_id is None and permission.job_id is None:
            return all_jobs

        if permission.job_id is not None:
            job_ids.add(permission.job_id)

        if permission.job_family_id is not None:
            job_ids.update(family_to_job_ids[permission.job_family_id])

    jobs: list[JobDto] = [id_to_job[fid] for fid in job_ids]
    return sorted(jobs, key=lambda job: (job.name, job.version))


def list_permitted_families(
    auth_subject: tables.AuthSubject,
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
    mapper = LifecycleCache.record_mapper()
    placeholder: str = mapper.placeholder
    subject_filter = QueryCondition(f'auth_subject_id = {placeholder}', auth_subject.id)
    scope_filter = QueryCondition.operator_or(
        QueryCondition(f'scope = {placeholder}', scope),
        QueryCondition(f'scope = {placeholder}', AuthScope.FULL_ACCESS.value),
    )
    filter_condition = QueryCondition.operator_and(
        subject_filter,
        scope_filter,
    )
    permissions = mapper.filter(tables.AuthResourcePermission, condition=filter_condition)

    id_to_family: dict[str, JobFamilyDto] = {f.id or '': f for f in all_families}
    family_ids = set()
    for permission in permissions:
        if permission.job_family_id is None and permission.job_id is None:
            return all_families

        if permission.job_family_id is not None:
            family_ids.add(permission.job_family_id)

    families: list[JobFamilyDto] = [id_to_family[id] for id in family_ids]
    return sorted(families, key=lambda family: family.name)


def grant_permission(
    auth_subject: tables.AuthSubject,
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
    if permission_exists(auth_subject, job_name, job_version, scope):
        subject_info = get_description_from_auth_subject(auth_subject)
        logger.warning(f'Permission for {subject_info} to {job_name} {job_version} (scope {scope}) is already granted')
        return

    mapper = LifecycleCache.record_mapper()
    if job_name and job_version:
        job_model = mapper.find_one(tables.Job, name=job_name, version=job_version)
        permission = tables.AuthResourcePermission(
            id=None,
            auth_subject_id=auth_subject.id,
            scope=scope,
            job_family_id=None,
            job_id=job_model.id,
            endpoint=None,
        )
        resource_description = f'job "{job_name} v{job_version}"'
    elif job_name:
        job_family_model = mapper.find_one(tables.JobFamily, name=job_name)
        permission = tables.AuthResourcePermission(
            id=None,
            auth_subject_id=auth_subject.id,
            scope=scope,
            job_family_id=job_family_model.id,
            job_id=None,
            endpoint=None,
        )
        resource_description = f'job family "{job_name}"'
    else:
        permission = tables.AuthResourcePermission(
            id=None,
            auth_subject_id=auth_subject.id,
            scope=scope,
            job_family_id=None,
            job_id=None,
            endpoint=None,
        )
        resource_description = 'all jobs'

    mapper.create(permission)
    subject_info = get_description_from_auth_subject(auth_subject)
    logger.info(f'"{subject_info}" has been granted permission to {resource_description} within {scope} scope')


def permission_exists(
    auth_subject: tables.AuthSubject,
    job_name: str | None,
    job_version: str | None,
    scope: str,
) -> bool:
    mapper = LifecycleCache.record_mapper()
    placeholder: str = mapper.placeholder
    table_permission = table_name(tables.AuthResourcePermission)
    table_family = table_name(tables.JobFamily)
    table_job = table_name(tables.Job)
    join_expression = f'left join {table_family} on {table_family}.id = {table_permission}.job_family_id'
    join_expression += f' left join {table_job} on {table_job}.id = {table_permission}.job_id'

    subject_filter = QueryCondition(f'{table_permission}.auth_subject_id = {placeholder}', auth_subject.id)
    scope_filter = QueryCondition(f'{table_permission}.scope = {placeholder}', scope)
    if job_name and job_version:
        resource_filter = QueryCondition.operator_and(
            QueryCondition(f'{table_job}.name = {placeholder}', job_name),
            QueryCondition(f'{table_job}.version = {placeholder}', job_version),
        )
    elif job_name:
        resource_filter = QueryCondition.operator_and(
            QueryCondition(f'{table_family}.name = {placeholder}', job_name),
            QueryCondition(f'{table_permission}.job_id is null'),
        )
    else:
        resource_filter = QueryCondition.operator_and(
            QueryCondition(f'{table_permission}.job_family_id is null'),
            QueryCondition(f'{table_permission}.job_id is null'),
        )
    filter_condition = QueryCondition.operator_and(
        subject_filter,
        resource_filter,
        scope_filter,
    )

    return mapper.exists_on_condition(
        tables.AuthResourcePermission, join_expression=join_expression, condition=filter_condition,
    )
