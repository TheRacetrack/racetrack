from functools import wraps
from typing import List

from fastapi import Request
from fastapi.responses import JSONResponse

from lifecycle.auth.authorize import authorize_internal_token, authorize_resource_access, authorize_scope_access, authorize_subject_type
from lifecycle.auth.authenticate import authenticate_token
from lifecycle.database.schema import tables
from lifecycle.server.cache import LifecycleCache
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from racetrack_commons.auth.auth import AuthSubjectType, UnauthorizedError
from racetrack_commons.auth.scope import AuthScope
from lifecycle.config import Config

logger = get_logger(__name__)


def check_auth(
    request: Request,
    subject_types: List[AuthSubjectType] | None = None,
    job_name: str | None = None,
    job_version: str | None = None,
    scope: AuthScope | None = None,
) -> tables.AuthSubject | None:
    """
    Authenticate and authorize the request
    :raise UnauthorizedError: If auth subject has no sufficient permissions
    """
    token_payload, auth_subject = authenticate_token(request)

    if subject_types:
        authorize_subject_type(token_payload, subject_types)

    if token_payload.subject_type == AuthSubjectType.INTERNAL.value:
        scope_str = scope.value if scope else None
        authorize_internal_token(token_payload, scope_str)
    else:
        assert auth_subject is not None
        if job_name:
            assert job_version, 'job_version is required when job_name is specified'
            assert scope is not None, 'scope is required when job_name is specified'
            authorize_resource_access(auth_subject, job_name, job_version, scope.value)
        elif scope:
            authorize_scope_access(auth_subject, scope.value)

    return auth_subject


def check_auth_decorator(
    request: Request,
    config: Config,
    subject_types: List[AuthSubjectType] | None = None,
    scope: AuthScope | None = None,
):
    """Decorator builder verifying auth token and type of logged auth subject"""
    def auth_decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):

            if not config.auth_required:
                return f(*args, **kwargs)

            try:
                token_payload, auth_subject = authenticate_token(request)
                if subject_types:
                    authorize_subject_type(token_payload, subject_types)

                if token_payload.subject_type == AuthSubjectType.INTERNAL.value:
                    scope_str = scope.value if scope else None
                    authorize_internal_token(token_payload, scope_str)
                elif scope:
                    assert auth_subject is not None
                    authorize_scope_access(auth_subject, scope.value)

            except UnauthorizedError as e:
                msg = e.describe(debug=config.auth_debug)
                log_exception(e)
                return JSONResponse(content={'error': msg}, status_code=401)

            return f(*args, **kwargs)

        return decorated
    return auth_decorator


def check_staff_user(
    request: Request,
) -> tables.AuthSubject:
    """
    Authenticate and authorize the request,
    checking if the request is being made by a staff user.
    :raise UnauthorizedError: If auth subject has no sufficient permissions
    """
    token_payload, auth_subject = authenticate_token(request)
    authorize_subject_type(token_payload, [AuthSubjectType.USER])
    assert auth_subject is not None
    username = token_payload.subject

    try:
        user: tables.User = LifecycleCache.record_mapper().find_one(tables.User, username=username)
    except EntityNotFound:
        raise UnauthorizedError(f'User {username} was not found')
    if not user.is_active:
        raise UnauthorizedError(f'User {username} is not active')
    if not user.is_staff:
        raise UnauthorizedError(f'User {username} is not a staff member')

    return auth_subject
