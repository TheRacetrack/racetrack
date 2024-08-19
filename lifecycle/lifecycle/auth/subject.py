import os
import uuid
from datetime import datetime

from lifecycle.database.condition_builder import QueryCondition
from lifecycle.database.schema import tables
from lifecycle.database.table_model import new_uuid
from lifecycle.server.cache import LifecycleCache
from racetrack_commons.auth.auth import AuthSubjectType
from racetrack_commons.auth.token import AuthTokenPayload, encode_jwt
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def get_auth_subject_by_user(user_model: tables.User) -> tables.AuthSubject:
    """Get or Create (if not exists) an auth subject for the given User"""
    mapper = LifecycleCache.record_mapper()
    try:
        return mapper.find_one(tables.AuthSubject, user_id=user_model.id)
    except EntityNotFound:
        pass

    auth_subject = tables.AuthSubject(
        id=new_uuid(),
        esc_id=None,
        user_id=user_model.id,
        job_family_id=None,
    )
    mapper.create(auth_subject)
    create_auth_token(auth_subject)
    logger.info(f'Created auth subject for user {user_model.username}')
    return auth_subject


def get_auth_subject_by_esc(esc_model: tables.Esc) -> tables.AuthSubject:
    """Get or Create (if not exists) an auth subject for the given ESC"""
    mapper = LifecycleCache.record_mapper()
    try:
        return mapper.find_one(tables.AuthSubject, esc_id=esc_model.id)
    except EntityNotFound:
        pass

    auth_subject = tables.AuthSubject(
        id=new_uuid(),
        esc_id=esc_model.id,
        user_id=None,
        job_family_id=None,
    )
    mapper.create(auth_subject)
    logger.info(f'Created auth subject for ESC {esc_model}')
    return auth_subject


def get_auth_subject_by_job_family(job_family: tables.JobFamily) -> tables.AuthSubject:
    """Get or Create (if not exists) an auth subject for the given Job Family"""
    mapper = LifecycleCache.record_mapper()
    try:
        return mapper.find_one(tables.AuthSubject, job_family_id=job_family.id)
    except EntityNotFound:
        pass

    auth_subject = tables.AuthSubject(
        id=new_uuid(),
        esc_id=None,
        user_id=None,
        job_family_id=job_family.id,
    )
    mapper.create(auth_subject)
    create_auth_token(auth_subject)
    logger.info(f'Created auth subject for Job Family {job_family}')
    return auth_subject


def get_auth_token_by_subject(auth_subject: tables.AuthSubject) -> tables.AuthToken:
    """Return FIRST auth token associated with the given auth subject. Create if missing."""
    mapper = LifecycleCache.record_mapper()
    try:
        auth_token: tables.AuthToken = mapper.find_one(tables.AuthToken, auth_subject_id=auth_subject.id)
        return auth_token
    except EntityNotFound:
        return create_auth_token(auth_subject)


def get_auth_tokens_by_subject(auth_subject: tables.AuthSubject) -> list[tables.AuthToken]:
    """Return all auth token associated with the given auth subject"""
    mapper = LifecycleCache.record_mapper()
    return mapper.find_many(tables.AuthToken, auth_subject_id=auth_subject.id)


def create_auth_token(auth_subject: tables.AuthSubject, expiry_time: datetime | None = None) -> tables.AuthToken:
    auth_token = tables.AuthToken(
        id=new_uuid(),
        auth_subject_id=auth_subject.id,
        token=generate_jwt_token(auth_subject),
        expiry_time=expiry_time,
        active=True,
        last_use_time=None,
    )
    LifecycleCache.record_mapper().create(auth_token)
    logger.info(f'Auth Token created for auth subject: {auth_subject}')
    return auth_token


def find_auth_subject_by_job_family_name(job_name: str) -> tables.AuthSubject:
    try:
        family = LifecycleCache.record_mapper().find_one(tables.JobFamily, name=job_name)
        return LifecycleCache.record_mapper().find_one(tables.AuthSubject, job_family_id=family.id)
    except EntityNotFound:
        raise EntityNotFound(f'Auth subject for Job family {job_name} not found')


def find_auth_subject_by_esc_id(esc_id: str) -> tables.AuthSubject:
    try:
        return LifecycleCache.record_mapper().find_one(tables.AuthSubject, esc_id=esc_id)
    except EntityNotFound:
        raise EntityNotFound(f'Auth subject for ESC {esc_id} not found')


def generate_jwt_token(auth_subject: tables.AuthSubject) -> str:
    subject_name = _get_subject_name_from_auth_subject(auth_subject)
    subject_type = _get_subject_type_from_auth_subject(auth_subject)
    payload = AuthTokenPayload(
        seed=str(uuid.uuid4()),
        subject=subject_name,
        subject_type=subject_type.value,
    )
    auth_secret_key = os.environ['AUTH_KEY']
    return encode_jwt(payload, auth_secret_key)


def regenerate_auth_tokens(auth_subject: tables.AuthSubject):
    mapper = LifecycleCache.record_mapper()
    auth_tokens = mapper.find_many(tables.AuthToken, auth_subject_id=auth_subject.id)
    for auth_token in auth_tokens:
        auth_token.token = generate_jwt_token(auth_subject)
        auth_token.last_use_time = None
        mapper.update(auth_token)


def regenerate_auth_token_by_id(auth_token_id: str):
    mapper = LifecycleCache.record_mapper()
    auth_token = mapper.find_one(tables.AuthToken, id=auth_token_id)
    auth_subject = mapper.find_one(tables.AuthSubject, id=auth_token.auth_subject_id)
    auth_token.token = generate_jwt_token(auth_subject)
    auth_token.last_use_time = None
    mapper.update(auth_token)
    logger.info(f'Auth token generated for auth subject ID: {auth_subject.id}')


def _get_subject_type_from_auth_subject(auth_subject: tables.AuthSubject) -> AuthSubjectType:
    if auth_subject.user_id is not None:
        return AuthSubjectType.USER
    elif auth_subject.esc_id is not None:
        return AuthSubjectType.ESC
    elif auth_subject.job_family_id is not None:
        return AuthSubjectType.JOB_FAMILY
    else:
        raise ValueError("Unknown auth_subject type")


def _get_subject_name_from_auth_subject(auth_subject: tables.AuthSubject) -> str:
    mapper = LifecycleCache.record_mapper()
    if auth_subject.user_id is not None:
        user = mapper.find_one(tables.User, id=auth_subject.user_id)
        return user.username
    elif auth_subject.esc_id is not None:
        esc = mapper.find_one(tables.Esc, id=auth_subject.esc_id)
        return esc.id
    elif auth_subject.job_family_id is not None:
        job_family = mapper.find_one(tables.JobFamily, id=auth_subject.job_family_id)
        return job_family.name
    else:
        raise ValueError("Unknown auth_subject type")


def get_description_from_auth_subject(auth_subject: tables.AuthSubject) -> str:
    mapper = LifecycleCache.record_mapper()
    if auth_subject.user_id is not None:
        user = mapper.find_one(tables.User, id=auth_subject.user_id)
        return f'User {user.username}'
    elif auth_subject.esc_id is not None:
        esc = mapper.find_one(tables.Esc, id=auth_subject.esc_id)
        return f'ESC {esc.name}'
    elif auth_subject.job_family_id is not None:
        job_family = mapper.find_one(tables.JobFamily, id=auth_subject.job_family_id)
        return f'Job family {job_family.name}'
    else:
        raise ValueError("Unknown auth_subject type")


def regenerate_specific_user_token(auth_subject: tables.AuthSubject) -> str:
    regenerate_auth_tokens(auth_subject)
    username = _get_subject_name_from_auth_subject(auth_subject)
    logger.info(f'Regenerated token of User {username}')
    auth_token = get_auth_token_by_subject(auth_subject)
    return auth_token.token


def regenerate_all_user_tokens():
    mapper = LifecycleCache.record_mapper()
    auth_subjects: list[tables.AuthSubject] = mapper.filter(
        tables.AuthSubject, condition=QueryCondition('"user_id" is not NULL'),
    )
    for auth_subject in auth_subjects:
        regenerate_auth_tokens(auth_subject)
    count = len(auth_subjects)
    logger.info(f'Regenerated tokens of all {count} Users')


def regenerate_all_job_family_tokens():
    mapper = LifecycleCache.record_mapper()
    auth_subjects: list[tables.AuthSubject] = mapper.filter(
        tables.AuthSubject, condition=QueryCondition('"job_family_id" is not NULL'),
    )
    for auth_subject in auth_subjects:
        regenerate_auth_tokens(auth_subject)
    count = len(auth_subjects)
    logger.info(f'Regenerated tokens of all {count} Job Families')


def regenerate_all_esc_tokens():
    mapper = LifecycleCache.record_mapper()
    auth_subjects: list[tables.AuthSubject] = mapper.filter(
        tables.AuthSubject, condition=QueryCondition('"esc_id" is not NULL'),
    )
    for auth_subject in auth_subjects:
        regenerate_auth_tokens(auth_subject)
    count = len(auth_subjects)
    logger.info(f'Regenerated tokens of all {count} ESCs')


def revoke_token(token_id: str):
    mapper = LifecycleCache.record_mapper()
    auth_token = mapper.find_one(tables.AuthToken, id=token_id)
    auth_subject = mapper.find_one(tables.AuthSubject, id=auth_token.auth_subject_id)
    subject_info = get_description_from_auth_subject(auth_subject)
    mapper.delete_record(auth_token)
    logger.info(f'Auth token "{token_id}" revoked. Subject: {subject_info}')
