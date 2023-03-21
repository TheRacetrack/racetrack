import json
import sys
from typing import Dict, Optional

from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import configure_logs, get_logger
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.request import parse_response, parse_response_object, Requests

logger = get_logger(__name__)


def call_job(
    name: str,
    version: str,
    remote: Optional[str],
    endpoint: str,
    payload_json: str,
    curl: bool,
):
    if curl:
        configure_logs(log_level='error')

    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, remote)
    user_auth = get_user_auth(client_config, lifecycle_url)

    r = Requests.get(
        f'{lifecycle_url}/api/v1/job/{name}/{version}',
        headers=get_auth_request_headers(user_auth),
    )
    job = parse_response_object(r, 'Lifecycle response error')
    pub_url = job.get('pub_url')
    payload_dict = json.loads(payload_json)
    full_url = f'{pub_url}{endpoint}'

    if curl:
        _print_curl_command(name, version, full_url, payload_json, user_auth)
        return

    logger.info(f'Calling job "{name} {version}" at {full_url}')
    r = Requests.post(
        full_url,
        json=payload_dict,
        headers=get_auth_request_headers(user_auth),
    )
    response_object = parse_response(r, 'Lifecycle response error')
    logger.info('Result:')
    print(str(response_object))


def _print_curl_command(
    name: str,
    version: str,
    full_url: str,
    payload_json: str,
    user_auth: str,
):
    print(f"""
    curl -X 'POST' \\
  '{full_url}' \\
  -H 'X-Racetrack-Auth: {user_auth}' \\
  -H 'Accept: application/json' \\
  -H 'Content-Type: application/json' \\
  -d '{payload_json}'
""".strip())
