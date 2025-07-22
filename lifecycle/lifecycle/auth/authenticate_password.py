from lifecycle.database.schema.tables import User
from lifecycle.server.cache import LifecycleCache
from racetrack_client.log.errors import EntityNotFound
from typing import Optional
from lifecycle.auth.hasher import get_hasher, make_password

UNUSABLE_PASSWORD_SUFFIX_LENGTH = 40
UNUSABLE_PASSWORD_PREFIX = "!"

def authenticate(username: str, password: str) -> Optional[User]:
    """
    If the given credentials are valid, return a User object.
    """
    try:
        user = authenticate_user(username, password)
    except PermissionDenied:
        return None

    return user

def authenticate_user(username: str, password: str) -> Optional[User]:
        try:
            user: User = LifecycleCache.record_mapper().find_one(User, username=username)
        except EntityNotFound:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user

            make_password(password)

            return None
        
        if check_password(password, user.password) and user.is_active:
            return user

        return None


class PermissionDenied(Exception):
    """The user did not have permission to do that"""
    pass


def check_password(password: str, encoded: str):
    hasher = get_hasher()
    is_correct = hasher.verify(password, encoded)

    return is_correct
