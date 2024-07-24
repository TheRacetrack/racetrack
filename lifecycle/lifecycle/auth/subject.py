import os
import uuid

from django.contrib.auth.models import User
from django.db.models import Q, QuerySet

from lifecycle.django.registry.database import db_access
from lifecycle.django.registry import models
from racetrack_commons.auth.auth import AuthSubjectType
from racetrack_commons.auth.token import AuthTokenPayload, encode_jwt
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


@db_access
def get_auth_subject_by_user(user_model: User) -> models.AuthSubject:
    """Get or Create (if not exists) an auth subject for the given User"""
    try:
        return models.AuthSubject.objects.get(user=user_model)
    except models.AuthSubject.DoesNotExist:
        pass

    auth_subject = models.AuthSubject()
    auth_subject.user = user_model
    auth_subject.save()
    create_auth_token(auth_subject)
    logger.info(f'Created auth subject for user {user_model.username}')
    return auth_subject


@db_access
def get_auth_subject_by_esc(esc_model: models.Esc) -> models.AuthSubject:
    """Get or Create (if not exists) an auth subject for the given ESC"""
    try:
        return models.AuthSubject.objects.get(esc=esc_model)
    except models.AuthSubject.DoesNotExist:
        pass

    auth_subject = models.AuthSubject()
    auth_subject.esc = esc_model
    auth_subject.save()
    create_auth_token(auth_subject)
    logger.info(f'Created auth subject for ESC {esc_model}')
    return auth_subject


@db_access
def get_auth_subject_by_job_family(job_family: models.JobFamily) -> models.AuthSubject:
    """Get or Create (if not exists) an auth subject for the given Job Family"""
    try:
        return models.AuthSubject.objects.get(job_family=job_family)
    except models.AuthSubject.DoesNotExist:
        pass

    auth_subject = models.AuthSubject()
    auth_subject.job_family = job_family
    auth_subject.save()
    create_auth_token(auth_subject)
    logger.info(f'Created auth subject for Job Family {job_family}')
    return auth_subject


def get_auth_token_by_subject(auth_subject: models.AuthSubject) -> models.AuthToken:
    """Return FIRST auth token associated with the given auth subject"""
    auth_tokens_queryset: QuerySet = models.AuthToken.objects.filter(auth_subject=auth_subject)
    auth_token: models.AuthToken | None = auth_tokens_queryset.first()
    if auth_token is None:
        return create_auth_token(auth_subject)
    return auth_token


def create_auth_token(auth_subject: models.AuthSubject) -> models.AuthToken:
    auth_token = models.AuthToken()
    auth_token.auth_subject = auth_subject
    auth_token.token = generate_jwt_token(auth_subject)
    auth_token.active = True
    auth_token.last_use_time = None
    auth_token.save()
    logger.info(f'Auth Token created for auth subject: {auth_subject}')
    return auth_token


@db_access
def find_auth_subject_by_job_family_name(job_name: str) -> models.AuthSubject:
    try:
        return models.AuthSubject.objects.get(job_family__name=job_name)
    except models.AuthSubject.DoesNotExist:
        raise EntityNotFound(f'Auth subject for Job family {job_name} not found')


@db_access
def find_auth_subject_by_esc_id(esc_id: str) -> models.AuthSubject:
    try:
        return models.AuthSubject.objects.get(esc__id=esc_id)
    except models.AuthSubject.DoesNotExist:
        raise EntityNotFound(f'Auth subject for ESC {esc_id} not found')


def generate_jwt_token(auth_subject: models.AuthSubject) -> str:
    subject_name = _get_subject_name_from_auth_subject(auth_subject)
    subject_type = _get_subject_type_from_auth_subject(auth_subject)
    payload = AuthTokenPayload(
        seed=str(uuid.uuid4()),
        subject=subject_name,
        subject_type=subject_type.value,
    )
    auth_secret_key = os.environ['AUTH_KEY']
    return encode_jwt(payload, auth_secret_key)


def regenerate_auth_tokens(auth_subject: models.AuthSubject):
    auth_tokens_queryset: QuerySet = models.AuthToken.objects.filter(auth_subject=auth_subject)
    for auth_token in auth_tokens_queryset:
        auth_token.token = generate_jwt_token(auth_subject)
        auth_token.last_use_time = None
        auth_token.save()


def regenerate_auth_token_by_id(auth_token_id: str):
    auth_token = models.AuthToken.objects.get(id=auth_token_id)
    auth_token.token = generate_jwt_token(auth_token.auth_subject)
    auth_token.last_use_time = None
    auth_token.save()
    logger.info(f'Auth token generated for auth subject ID: {auth_token.auth_subject.id}')


def _get_subject_type_from_auth_subject(auth_subject: models.AuthSubject) -> AuthSubjectType:
    if auth_subject.user is not None:
        return AuthSubjectType.USER
    elif auth_subject.esc is not None:
        return AuthSubjectType.ESC
    elif auth_subject.job_family is not None:
        return AuthSubjectType.JOB_FAMILY
    else:
        raise ValueError("Unknown auth_subject type")


def _get_subject_name_from_auth_subject(auth_subject: models.AuthSubject) -> str:
    if auth_subject.user is not None:
        return auth_subject.user.username
    elif auth_subject.esc is not None:
        return auth_subject.esc.id
    elif auth_subject.job_family is not None:
        return auth_subject.job_family.name
    else:
        raise ValueError("Unknown auth_subject type")


def get_description_from_auth_subject(auth_subject: models.AuthSubject) -> str:
    if auth_subject.user is not None:
        return f'User {auth_subject.user.username}'
    elif auth_subject.esc is not None:
        return f'ESC {auth_subject.esc.name}'
    elif auth_subject.job_family is not None:
        return f'Job family {auth_subject.job_family.name}'
    else:
        raise ValueError("Unknown auth_subject type")


def regenerate_specific_user_token(auth_subject: models.AuthSubject) -> str:
    regenerate_auth_tokens(auth_subject)
    logger.info(f'Regenerated token of User {auth_subject.user.username}')
    auth_token = get_auth_token_by_subject(auth_subject)
    return auth_token.token


def regenerate_all_user_tokens():
    auth_subject_queryset = models.AuthSubject.objects.filter(Q(user__isnull=False))
    for auth_subject in auth_subject_queryset:
        regenerate_auth_tokens(auth_subject)
    count = auth_subject_queryset.count()
    logger.info(f'Regenerated tokens of all {count} Users')


def regenerate_all_job_family_tokens():
    auth_subject_queryset = models.AuthSubject.objects.filter(Q(job_family__isnull=False))
    for auth_subject in auth_subject_queryset:
        regenerate_auth_tokens(auth_subject)
    count = auth_subject_queryset.count()
    logger.info(f'Regenerated tokens of all {count} Job Families')


def regenerate_all_esc_tokens():
    auth_subject_queryset = models.AuthSubject.objects.filter(Q(esc__isnull=False))
    for auth_subject in auth_subject_queryset:
        regenerate_auth_tokens(auth_subject)
    count = auth_subject_queryset.count()
    logger.info(f'Regenerated tokens of all {count} ESCs')
