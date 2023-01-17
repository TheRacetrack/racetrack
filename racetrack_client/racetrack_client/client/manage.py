from typing import Dict, List, Optional

from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.request import parse_response, parse_response_list, Requests
from racetrack_client.utils.table import print_table


logger = get_logger(__name__)


def list_fatmen(remote: Optional[str]):
    """List all deployed fatmen"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, remote)
    user_auth = get_user_auth(client_config, lifecycle_url)

    r = Requests.get(
        f'{lifecycle_url}/api/v1/fatman',
        headers=get_auth_request_headers(user_auth),
    )
    fatmen: List[Dict] = parse_response_list(r, 'Lifecycle response error')

    if not fatmen:
        logger.info(f'No fatmen deployed at {lifecycle_url}.')
        return

    logger.info(f'List of all fatmen ({len(fatmen)}) deployed at {lifecycle_url}:')
    table: List[List[str]] = []
    table.append(['NAME', 'VERSION', 'STATUS', 'DEPLOYED BY'])
    for fatman in fatmen:
        name = fatman.get('name', '')
        version = fatman.get('version', '')
        status = fatman.get('status', '').upper()
        deployed_by = fatman.get('deployed_by', '')
        table.append([name, version, status, deployed_by])
    print_table(table)


def move_fatman(remote: Optional[str], fatman_name: str, fatman_version: str, new_infra_target: str):
    """Move fatman from one infrastructure target to another"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, remote)
    user_auth = get_user_auth(client_config, lifecycle_url)

    logger.info(f'Moving fatman "{fatman_name}" v{fatman_version} at {lifecycle_url} to {new_infra_target} infrastructure...')
    r = Requests.post(
        f'{lifecycle_url}/api/v1/fatman/{fatman_name}/{fatman_version}/move',
        json={
            'infrastructure_target': new_infra_target,
        },
        headers=get_auth_request_headers(user_auth),
    )
    parse_response(r, 'Lifecycle response error')
    logger.info(f'Fatman "{fatman_name}" v{fatman_version} at {lifecycle_url} has been moved to {new_infra_target} infrastructure ')


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
