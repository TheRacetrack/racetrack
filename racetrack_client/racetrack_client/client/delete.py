from typing import Optional

from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.request import parse_response, Requests


logger = get_logger(__name__)


def delete_fatman(name: str, version: str, remote: Optional[str]):
    """Delete versioned fatman instance"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, remote)
    user_auth = get_user_auth(client_config, lifecycle_url)

    logger.debug(f'Deleting fatman "{name}" v{version} from {lifecycle_url}...')
    r = Requests.delete(
        f'{lifecycle_url}/api/v1/fatman/{name}/{version}',
        headers=get_auth_request_headers(user_auth),
    )
    parse_response(r, 'Lifecycle response error')
    logger.info(f'Fatman "{name}" v{version} has been deleted from {lifecycle_url}')
