import json
from typing import Dict, Optional

import yaml

from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.context_error import wrap_context
from racetrack_client.log.logs import configure_logs, get_logger
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.request import parse_response, parse_response_object, Requests

logger = get_logger(__name__)


def call_job(
    name: str,
    version: str,
    remote: Optional[str],
    endpoint: str,
    payload: str,
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
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
    full_url = f'{pub_url}{endpoint}'
    payload_dict = _parse_payload(payload)

    if curl:
        _print_curl_command(full_url, payload_dict, user_auth)
        return

    logger.info(f'Calling job "{name} {version}" at {full_url}')
    r = Requests.post(
        full_url,
        json=payload_dict,
        headers=get_auth_request_headers(user_auth),
    )

    response_object = parse_response(r, 'Lifecycle response error')
    logger.info('Response:')
    response_str = json.dumps(response_object, indent=4)
    print(response_str)


def _parse_payload(payload: str) -> Dict:
    with wrap_context('parsing payload'):
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            obj = yaml.load(payload, Loader=yaml.FullLoader)
        assert isinstance(obj, dict), 'given payload is not a key-value dictionary'
        return obj
        

def _print_curl_command(
    full_url: str,
    payload_dict: Dict,
    user_auth: str,
):
    payload_json = json.dumps(payload_dict, indent=2)
    print(f"""
    curl -X 'POST' \\
  '{full_url}' \\
  -H 'X-Racetrack-Auth: {user_auth}' \\
  -H 'Accept: application/json' \\
  -H 'Content-Type: application/json; charset=utf-8' \\
  -d '{payload_json}'
""".strip())
