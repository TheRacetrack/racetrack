from __future__ import annotations
import logging
import os
from urllib.parse import quote

from django.db.utils import OperationalError, InterfaceError
from django.http import HttpResponse

from racetrack_client.log.context_error import ContextError
from racetrack_client.utils.auth import RT_AUTH_HEADER
from dashboard.session import RT_SESSION_USER_AUTH_KEY


class UserCookieMiddleWare(object):
    """
    Middleware to set user cookie
    If user is authenticated and there is no cookie, set the cookie.
    If the user is not authenticated and the cookie remains, delete it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        cookie_domain = os.environ.get('CLUSTER_FQDN', None)
        if cookie_domain:
            racetrack_subdomain = os.environ.get('RACETRACK_SUBDOMAIN', 'racetrack')
            cookie_domain = f'{racetrack_subdomain}.{cookie_domain}'

        try:
            user_authenticated = request.user.is_authenticated
        except OperationalError as e:
            raise ContextError("Database connection: OperationalError", e)
        except InterfaceError as e:
            raise ContextError("Database connection: InterfaceError", e)

        if user_authenticated and not request.COOKIES.get(RT_AUTH_HEADER):

            auth_token = request.session.get(RT_SESSION_USER_AUTH_KEY)
            if auth_token is None:
                logging.error("UserCookieMiddleware: user_auth from session is empty")
                return response
        
            set_auth_token_cookie(auth_token, response)

        elif not user_authenticated:
            if request.COOKIES.get(RT_AUTH_HEADER):
                response.delete_cookie(
                    key=RT_AUTH_HEADER,
                    path='/',
                    domain=_get_cookie_domain())

        return response


def set_auth_token_cookie(auth_token: str, response: HttpResponse):
    # if cookie value contains /, it would get unnecessarily double quoted, so encode
    value = quote(auth_token, safe="")

    # Domain defines the host to which the cookie will be sent.
    # Empty domain means that cookie will be created for current host, not including subdomains.
    # if specified, then subdomains are included.
    response.set_cookie(
        key=RT_AUTH_HEADER,
        value=value,
        path='/',
        domain=_get_cookie_domain(),
        max_age=60 * 60 * 24 * 365,  # one year of cookie lifetime (in seconds), also makes cookie persist between browser restarts
        samesite='lax',  # cookie is sent only when user access origin site or navigates to it, prevents CSRF
        httponly=True,  # prevents client-side JavaScript read access
        secure=True)  # cookie is sent only when request is made with https (except on localhost)


def _get_cookie_domain() -> str | None:
    cookie_domain = os.environ.get('CLUSTER_FQDN', None)
    if not cookie_domain:
        return cookie_domain
    racetrack_subdomain = os.environ.get('RACETRACK_SUBDOMAIN', 'racetrack')
    return f'{racetrack_subdomain}.{cookie_domain}'
