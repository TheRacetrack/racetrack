from typing import Optional

from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest.validate import load_validated_manifest
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.request import parse_response, Requests


logger = get_logger(__name__)


def delete_fatman(workdir: str, lifecycle_url: Optional[str], version: Optional[str]):
    """Delete versioned fatman instance"""
    client_config = load_client_config()
    manifest = load_validated_manifest(workdir)
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)

    version = version or manifest.version

    logger.debug(f'Deleting fatman "{manifest.name}" v{version} from {lifecycle_url}...')
    r = Requests.delete(
        f'{lifecycle_url}/api/v1/fatman/{manifest.name}/{version}',
        headers=get_auth_request_headers(user_auth),
    )
    parse_response(r, 'Lifecycle response error')
    logger.info(f'Fatman "{manifest.name}" v{version} has been deleted from {lifecycle_url}')
