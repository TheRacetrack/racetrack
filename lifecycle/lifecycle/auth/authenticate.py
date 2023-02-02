import os
from typing import Optional, Tuple

from fastapi import Request

from lifecycle.django.registry.database import db_access
from lifecycle.django.registry import models
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.auth import RT_AUTH_HEADER
from racetrack_client.utils.time import datetime_to_timestamp, now
from racetrack_commons.auth.auth import AuthSubjectType, UnauthorizedError
from racetrack_commons.auth.token import AuthTokenPayload, decode_jwt, verify_and_decode_jwt

logger = get_logger(__name__)


def authenticate_token(request: Request) -> Tuple[AuthTokenPayload, Optional[models.AuthSubject]]:
    """Ensure request has valid token and recognize identity of the requester"""
    auth_token = get_current_auth_token(request)

    auth_secret_key = os.environ.get('AUTH_KEY')
    token_payload = verify_and_decode_jwt(auth_token, auth_secret_key)
    if token_payload.subject_type == AuthSubjectType.INTERNAL.value:
        return token_payload, None

    try:
        auth_subject = find_auth_subject_by_token(auth_token)
    except EntityNotFound:
        raise UnauthorizedError('wrong credentials: token is unknown', 'token was not found in the database')

    validate_auth_subject_access(auth_subject)
    return token_payload, auth_subject


def get_current_auth_token(request: Request) -> str:
    auth_token = read_auth_token_header(request)
    if not auth_token:
        raise UnauthorizedError(f'auth token not found in a header {RT_AUTH_HEADER}')
    return auth_token


def read_auth_token_header(request: Request) -> Optional[str]:
    auth_token = request.headers.get(RT_AUTH_HEADER)
    # TODO: abandon backward compatibility with old headers
    if not auth_token:
        auth_token = request.headers.get("X-Racetrack-User-Auth")
    if not auth_token:
        auth_token = request.headers.get("X-Racetrack-Job-Auth")
    if not auth_token:
        auth_token = request.headers.get("X-Racetrack-Esc-Auth")
    return auth_token


@db_access
def find_auth_subject_by_token(token: str) -> models.AuthSubject:
    try:
        return models.AuthSubject.objects.get(token=token)
    except models.AuthSubject.DoesNotExist:
        raise EntityNotFound('Auth Subject with given token was not found')


def get_username_from_token(request: Request) -> str:
    auth_token = get_current_auth_token(request)
    token_payload = decode_jwt(auth_token)
    return token_payload.subject


def validate_auth_subject_access(subject: models.AuthSubject):
    """Check if auth subject still has access or it has been revoked or expired"""
    if not subject.active:
        raise UnauthorizedError('subject access has been revoked')

    if subject.expiry_time is not None:
        if datetime_to_timestamp(now()) > subject.expiry_time:
            raise UnauthorizedError('subject access has expired')
