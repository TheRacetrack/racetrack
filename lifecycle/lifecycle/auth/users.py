from django.contrib import auth as django_auth
from django.contrib.auth.models import User

from lifecycle.auth.subject import regenerate_auth_token
from lifecycle.auth.subject import get_auth_subject_by_user
from lifecycle.django.registry import models
from lifecycle.django.registry.database import db_access
from racetrack_commons.auth.auth import UnauthorizedError
from racetrack_client.log.logs import get_logger
from racetrack_commons.auth.scope import AuthScope

logger = get_logger(__name__)


@db_access
def authenticate_username_with_password(username: str, password: str) -> tuple[User, models.AuthSubject]:
    user: User = django_auth.authenticate(username=username, password=password)
    if user is None:
        raise UnauthorizedError('incorrect username or password')
    if not user.is_active:
        raise UnauthorizedError('user account is disabled')

    auth_subject = get_auth_subject_by_user(user=user)
    return user, auth_subject


@db_access
def register_user_account(username: str, password: str) -> User:
    user = User.objects.create_user(username, password=password)
    user.is_active = False

    auth_subject = create_auth_subject_for_user(user)
    # grant default user permisssions
    grant_permission(auth_subject, AuthScope.READ_JOB.value)
    grant_permission(auth_subject, AuthScope.CALL_JOB.value)
    grant_permission(auth_subject, AuthScope.DEPLOY_NEW_FAMILY.value)
    grant_permission(auth_subject, AuthScope.DEPLOY_JOB.value)

    logger.info(f'User account created: {username}')
    return user


@db_access
def change_user_password(username: str, old_password: str, new_password: str):
    user: User = django_auth.authenticate(username=username, password=old_password)
    if user is None:
        raise UnauthorizedError('current password is incorrect')

    user.set_password(new_password)
    user.save()
    logger.debug(f'User {username} changed password')


def create_auth_subject_for_user(user_model: User) -> models.AuthSubject:
    auth_subject = models.AuthSubject()
    auth_subject.user = user_model
    auth_subject.token = ''
    auth_subject.active = True
    auth_subject.save()
    regenerate_auth_token(auth_subject)
    return auth_subject


def grant_permission(
    auth_subject: models.AuthSubject,
    scope: str,
):
    permission = models.AuthResourcePermission(
        auth_subject=auth_subject,
        scope=scope,
    )
    permission.save()
    logger.info(f'"{auth_subject}" has been granted permission to all jobs within {scope} scope')
