import re
from functools import wraps

from django.conf import settings
from django.shortcuts import redirect

from racetrack_client.utils.auth import RT_AUTH_HEADER
from racetrack_commons.auth.auth import UnauthorizedError
from racetrack_commons.auth.token import decode_jwt


def login_required(view_func):

    def wrapped_view(request, *args, **kwargs):
        if settings.AUTH_REQUIRED:
            if not request.COOKIES.get(RT_AUTH_HEADER):
                return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))
        return view_func(request, *args, **kwargs)

    return wraps(view_func)(wrapped_view)


def get_auth_token(request) -> str:
    auth_token = request.COOKIES.get(RT_AUTH_HEADER)
    if not auth_token and not settings.AUTH_REQUIRED:
        return ''
    if not auth_token:
        raise UnauthorizedError('no Auth Token set, please log in.')
    decode_jwt(auth_token)
    return auth_token


def remove_ansi_sequences(content: str) -> str:
    """Remove ANSI escape codes controlling font colors"""
    return re.sub(r'\x1b\[\d+(;\d+)?m', '', content)
