from datetime import datetime
from typing import Optional

from lifecycle.auth.authenticate_password import authenticate
from lifecycle.auth.hasher import make_password
from lifecycle.auth.subject import create_auth_token, get_auth_token_by_subject, get_description_from_auth_subject
from lifecycle.auth.subject import get_auth_subject_by_user
from lifecycle.auth.validate import ValidationError, validate_password
from lifecycle.database.schema import tables
from lifecycle.database.table_model import new_uuid
from lifecycle.server.cache import LifecycleCache
from racetrack_commons.auth.auth import UnauthorizedError
from racetrack_client.log.logs import get_logger
from racetrack_commons.auth.scope import AuthScope
from racetrack_client.log.errors import EntityNotFound

logger = get_logger(__name__)


def authenticate_username_with_password(username: str, password: str) -> tuple[tables.User, tables.AuthSubject, tables.AuthToken]:
    user: Optional[tables.User] = authenticate(username=username, password=password)
    if user is None:
        raise UnauthorizedError('incorrect username or password')

    user_record = find_user_record_by_id(user.id)
    auth_subject = get_auth_subject_by_user(user_record)
    auth_token = get_auth_token_by_subject(auth_subject)
    return user, auth_subject, auth_token


def register_user_account(username: str, password: str) -> tables.User:
    try:
        validate_password(password)
    except ValidationError as e:
        raise RuntimeError('Invalid password: ' + str(e))

    try:
        LifecycleCache.record_mapper().find_one(tables.User, username=username)
        raise RuntimeError(f'Username already exists: {username}')
    except EntityNotFound:
        pass

    user = LifecycleCache.record_mapper().create_from_dict(
        tables.User, 
        {
            "username": username,
            "password": make_password(password),
            "is_active": False,
            "first_name": "",
            "last_name": "",
            "email": "",
            "is_staff": False,
            "is_superuser": False,
            "date_joined": datetime.now(),
            "last_login": None,
        }
    )

    user_record = find_user_record_by_id(user['id'])

    auth_subject = create_auth_subject_for_user(user_record)
    # grant default user permisssions
    grant_permission(auth_subject, AuthScope.READ_JOB.value)
    grant_permission(auth_subject, AuthScope.CALL_JOB.value)
    grant_permission(auth_subject, AuthScope.DEPLOY_NEW_FAMILY.value)
    grant_permission(auth_subject, AuthScope.DEPLOY_JOB.value)

    logger.info(f'User account created: {username}')
    return user


def change_user_password(username: str, old_password: str, new_password: str):
    user: Optional[tables.User] = authenticate(username=username, password=old_password)
    if user is None:
        raise UnauthorizedError('Passed password is incorrect.')

    try:
        validate_password(new_password)
    except ValidationError as e:
        raise RuntimeError('Invalid password: ' + str(e))

    user.password = make_password(new_password)
    LifecycleCache.record_mapper().update(user)
    logger.debug(f'User {username} changed password')


def create_auth_subject_for_user(user_model: tables.User) -> tables.AuthSubject:
    auth_subject = tables.AuthSubject(
        id=new_uuid(),
        user_id=user_model.id,
        esc_id=None,
        job_family_id=None,
    )
    LifecycleCache.record_mapper().create(auth_subject)
    create_auth_token(auth_subject)
    return auth_subject


def grant_permission(
    auth_subject: tables.AuthSubject,
    scope: str,
):
    permission = tables.AuthResourcePermission(
        id=None,
        auth_subject_id=auth_subject.id,
        scope=scope,
        job_family_id=None,
        job_id=None,
        endpoint=None,
    )
    LifecycleCache.record_mapper().create(permission)
    subject_info = get_description_from_auth_subject(auth_subject)
    logger.info(f'"{subject_info}" has been granted permission to all jobs within {scope} scope')


def find_user_record_by_id(user_id: int) -> tables.User:
    return LifecycleCache.record_mapper().find_one(tables.User, id=user_id)
