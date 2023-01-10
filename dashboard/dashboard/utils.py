from functools import wraps
import re

from django.conf import settings
from django.shortcuts import redirect

from dashboard.session import RT_SESSION_USER_AUTH_KEY


def login_required(view_func):

    def wrapped_view(request, *args, **kwargs):
        if settings.AUTH_REQUIRED:
            if not request.user.is_authenticated or not request.session.get(RT_SESSION_USER_AUTH_KEY):
                return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))
        return view_func(request, *args, **kwargs)

    return wraps(view_func)(wrapped_view)


def remove_ansi_sequences(content: str) -> str:
    """Remove ANSI escape codes controlling font colors"""
    return re.sub(r'\x1b\[\d+(;\d+)?m', '', content)
