from typing import Optional

from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.request import parse_response, Requests


logger = get_logger(__name__)


def move_job(lifecycle_url: Optional[str], job_name: str, job_version: str, new_infra_target: str):
    """Move job from one infrastructure target to another"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)

    logger.info(f'Moving job "{job_name}" v{job_version} at {lifecycle_url} to {new_infra_target} infrastructure...')
    r = Requests.post(
        f'{lifecycle_url}/api/v1/job/{job_name}/{job_version}/move',
        json={
            'infrastructure_target': new_infra_target,
        },
        headers=get_auth_request_headers(user_auth),
    )
    parse_response(r, 'Lifecycle response error')
    logger.info(f'Job "{job_name}" v{job_version} at {lifecycle_url} has been moved to {new_infra_target} infrastructure ')
