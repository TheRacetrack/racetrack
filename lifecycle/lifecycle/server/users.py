from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404

from lifecycle.auth.subject import get_auth_subject_by_user, regenerate_auth_token
from lifecycle.django.registry.database import db_access
from racetrack_client.log.errors import EntityNotFound
from racetrack_client.log.logs import get_logger
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.entities.dto import UserProfileDto
from lifecycle.django.registry import models

logger = get_logger(__name__)


@db_access
def read_user_profile(username: str) -> UserProfileDto:
    try:
        user = get_object_or_404(User, username=username)
        auth_subject = get_auth_subject_by_user(user)
        return UserProfileDto(
            username=user.username,
            token=auth_subject.token,
        )
    except Http404:
        raise EntityNotFound(f'User was not found: {username}')


# Adding here @db_access makes adding new user through RT admin panel fail
# with "django.db.utils.InterfaceError: connection already closed" ; so it's protected in endpoints.py
def init_user_profile(username: str) -> UserProfileDto:
    """
    Creates Auth Subject profile for a user, and initializes it with auth token
    """
    try:
        user = get_object_or_404(User, username=username)
    except Http404:
        raise EntityNotFound(f'User was not found: {username}')

    auth_subject = create_auth_subject_for_user(user)

    # grant default user permisssions
    grant_permission(auth_subject, AuthScope.READ_JOB.value)
    grant_permission(auth_subject, AuthScope.CALL_JOB.value)
    grant_permission(auth_subject, AuthScope.DEPLOY_NEW_FAMILY.value)
    grant_permission(auth_subject, AuthScope.DEPLOY_JOB.value)

    logger.info(f"Created Auth Subject for user {username}")
    return UserProfileDto(
        username=user.username,
        token=auth_subject.token,
    )


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
