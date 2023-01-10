from enum import Enum
from typing import Dict

from racetrack_client.utils.request import parse_response_object, Requests


RT_AUTH_HEADER = 'X-Racetrack-Auth'


class RacetrackAuthMethod(Enum):
    TOKEN = 'racetrackAuth'


class AuthError(RuntimeError):
    def __init__(self, cause: str):
        super().__init__()
        self.cause = cause

    def __str__(self):
        return f'authentication error: {self.cause}'


def get_auth_request_headers(user_auth: str) -> Dict:
    return {
        RT_AUTH_HEADER: user_auth if user_auth != "" else None
    }


def is_auth_required(lifecycle_url: str) -> bool:
    r = Requests.get(
        f'{lifecycle_url}/api/v1/info',
    )
    response = parse_response_object(r, 'Lifecycle response error')
    return response["auth_required"]


def validate_user_auth(lifecycle_url: str, user_auth: str) -> str:
    r = Requests.get(
        f'{lifecycle_url}/api/v1/users/validate_user_auth',
        headers=get_auth_request_headers(user_auth),
    )
    if r.status_code == 401:
        raise AuthError('Invalid Auth Token')

    response = parse_response_object(r, 'Lifecycle response error')
    return response['username']
