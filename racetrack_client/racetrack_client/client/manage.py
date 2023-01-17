from enum import Enum
from typing import Dict, List, Optional

from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.request import parse_response, parse_response_list, Requests
from racetrack_client.utils.table import print_table
from racetrack_client.utils.time import nullable_timestamp_pretty_ago


logger = get_logger(__name__)


class FatmenListColumn(str, Enum):
    infrastructure = "infrastructure"
    deployed_by = "deployed_by"
    updated_at = "updated_at"
    last_call_at = "last_call_at"
    all = "all"


def list_fatmen(remote: Optional[str], columns: List[FatmenListColumn]):
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

    header = ['NAME', 'VERSION', 'STATUS']
    if FatmenListColumn.infrastructure in columns or FatmenListColumn.all in columns:
        header.append('INFRASTRUCTURE')
    if FatmenListColumn.deployed_by in columns or FatmenListColumn.all in columns:
        header.append('DEPLOYED BY')
    if FatmenListColumn.updated_at in columns or FatmenListColumn.all in columns:
        header.append('UPDATED AT')
    if FatmenListColumn.last_call_at in columns or FatmenListColumn.all in columns:
        header.append('LAST CALL AT')

    table: List[List[str]] = [header]
    for fatman in fatmen:
        name = fatman.get('name')
        version = fatman.get('version')
        status = fatman.get('status', '').upper()
        cells = [name, version, status]

        if FatmenListColumn.infrastructure in columns or FatmenListColumn.all in columns:
            cells.append(fatman.get('infrastructure_target'))
        if FatmenListColumn.deployed_by in columns or FatmenListColumn.all in columns:
            cells.append(fatman.get('deployed_by'))
        if FatmenListColumn.updated_at in columns or FatmenListColumn.all in columns:
            update_time = fatman.get('update_time')
            updated_ago = nullable_timestamp_pretty_ago(update_time)
            cells.append(updated_ago)
        if FatmenListColumn.last_call_at in columns or FatmenListColumn.all in columns:
            last_call_time = fatman.get('last_call_time')
            last_call_ago = nullable_timestamp_pretty_ago(last_call_time)
            cells.append(last_call_ago)

        table.append(cells)

    logger.info(f'List of all fatmen ({len(fatmen)}) deployed at {lifecycle_url}:')
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
