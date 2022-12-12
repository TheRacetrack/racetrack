from __future__ import annotations
import os
from typing import Any

from racetrack_client.utils.auth import RT_AUTH_HEADER
from racetrack_client.utils.request import Requests, parse_response, parse_response_object
from racetrack_client.utils.url import trim_url


class LifecycleClient:

    def __init__(self, auth_token: str = ''):
        self._lifecycle_api_url = trim_url(os.environ.get('LIFECYCLE_URL', 'http://localhost:7202'))
        self.auth_token = auth_token

    def request(self, method: str, path: str, **kwargs) -> Any:
        r = Requests.request(method,
                             f'{self._lifecycle_api_url}{path}',
                             headers=self._get_auth_headers(),
                             **kwargs)
        return parse_response(r, 'Lifecycle response')

    def request_dict(self, method: str, path: str, **kwargs) -> dict:
        r = Requests.request(method,
                             f'{self._lifecycle_api_url}{path}',
                             headers=self._get_auth_headers(),
                             **kwargs)
        return parse_response_object(r, 'Lifecycle response')

    def request_list(self, method: str, path: str, **kwargs) -> list:
        r = Requests.request(method,
                             f'{self._lifecycle_api_url}{path}',
                             headers=self._get_auth_headers(),
                             **kwargs)
        return parse_response_object(r, 'Lifecycle response')

    def _get_auth_headers(self) -> dict[str, str | None]:
        return {
            RT_AUTH_HEADER: self.auth_token if self.auth_token != "" else None
        }
