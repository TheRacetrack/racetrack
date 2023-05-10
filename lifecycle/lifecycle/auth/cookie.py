from __future__ import annotations
import os
from urllib.parse import quote

from fastapi.responses import Response

from racetrack_client.utils.auth import RT_AUTH_HEADER


def set_auth_token_cookie(auth_token: str, response: Response):
    # if cookie value contains /, it would get unnecessarily double quoted, so encode
    value = quote(auth_token, safe="")
    secure_cookie: bool = os.environ.get('ENFORCE_SECURE_COOKIE') == 'true'

    # Domain defines the host to which the cookie will be sent.
    # Empty domain means that cookie will be created for current host, not including subdomains.
    # if specified, then subdomains are included.
    response.set_cookie(
        key=RT_AUTH_HEADER,
        value=value,
        path='/',
        domain=_get_cookie_domain(),
        max_age=60 * 60 * 24 * 31,  # one month of cookie lifetime (in seconds), also makes cookie persist between browser restarts
        samesite='lax',  # cookie is sent only when user access origin site or navigates to it, prevents CSRF
        httponly=False,  # prevents client-side JavaScript read access
        secure=secure_cookie)  # whether cookie may only be transmitted using a secure https connection (except on localhost)


def delete_auth_cookie(response: Response):
    response.delete_cookie(
        key=RT_AUTH_HEADER,
        path='/',
        domain=_get_cookie_domain())


def _get_cookie_domain() -> str | None:
    cookie_domain = os.environ.get('CLUSTER_FQDN', None)
    if not cookie_domain:
        return cookie_domain
    racetrack_subdomain = os.environ.get('RACETRACK_SUBDOMAIN', 'racetrack')
    return f'{racetrack_subdomain}.{cookie_domain}'
