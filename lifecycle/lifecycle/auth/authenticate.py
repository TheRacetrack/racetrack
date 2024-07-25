import os
from typing import Tuple

from fastapi import Request

from lifecycle.django.registry import models
from lifecycle.django.registry.database import db_access
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.auth import RT_AUTH_HEADER
from racetrack_client.utils.time import datetime_to_timestamp, now
from racetrack_commons.auth.auth import AuthSubjectType, UnauthorizedError
from racetrack_commons.auth.token import AuthTokenPayload, decode_jwt, verify_and_decode_jwt

logger = get_logger(__name__)


def authenticate_token(request: Request) -> Tuple[AuthTokenPayload, models.AuthSubject | None]:
    """Ensure request has valid token and recognize identity of the requester"""
    jwt_token: str = get_current_jwt_token(request)

    auth_secret_key = os.environ['AUTH_KEY']
    token_payload: AuthTokenPayload = verify_and_decode_jwt(jwt_token, auth_secret_key)
    if token_payload.subject_type == AuthSubjectType.INTERNAL.value:
        return token_payload, None

    try:
        auth_subject, auth_token = find_auth_subject_by_token(jwt_token)
    except EntityNotFound:
        raise UnauthorizedError('wrong credentials: token is unknown', 'token was not found in the database')

    validate_auth_token_access(auth_token)
    _save_token_use(auth_token)
    return token_payload, auth_subject


def get_current_jwt_token(request: Request) -> str:
    auth_token = read_auth_token_header(request)
    if not auth_token:
        raise UnauthorizedError(f'auth token not found in a header {RT_AUTH_HEADER}')
    return auth_token


def read_auth_token_header(request: Request) -> str | None:
    auth_token = request.headers.get(RT_AUTH_HEADER)
    # TODO: abandon backward compatibility with old headers
    if not auth_token:
        auth_token = request.headers.get("X-Racetrack-User-Auth")
    if not auth_token:
        auth_token = request.headers.get("X-Racetrack-Esc-Auth")
    return auth_token


@db_access
def find_auth_subject_by_token(token: str) -> tuple[models.AuthSubject, models.AuthToken]:
    try:
        auth_token: models.AuthToken = models.AuthToken.objects.get(token=token)
        return auth_token.auth_subject, auth_token
    except models.AuthToken.DoesNotExist:
        raise EntityNotFound('given Auth Token was not found in the database')


def _save_token_use(auth_token: models.AuthToken):
    """
    Update date of the last use of the auth token.
    Keep it in daily granulatiry to avoid too many updates in the database.
    """
    if auth_token.last_use_time is None or auth_token.last_use_time.date() != now().date():
        auth_token.last_use_time = now()
        auth_token.save()


def get_username_from_token(request: Request) -> str:
    auth_token = get_current_jwt_token(request)
    token_payload = decode_jwt(auth_token)
    return token_payload.subject


def validate_auth_token_access(auth_token: models.AuthToken):
    """Check if auth token has valid access - hasn't been revoked and hasn't expired"""
    if not auth_token.active:
        raise UnauthorizedError('given access token has been revoked')

    if auth_token.expiry_time is not None:
        if datetime_to_timestamp(now()) > auth_token.expiry_time.timestamp():
            raise UnauthorizedError('given access token has expired')
