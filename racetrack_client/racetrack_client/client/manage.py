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


class JobTableColumn(str, Enum):
    infrastructure = "infrastructure"
    deployed_by = "deployed_by"
    updated_at = "updated_at"
    last_call_at = "last_call_at"
    pub_url = "pub_url"
    all = "all"


def list_jobs(remote: Optional[str], columns: List[JobTableColumn]):
    """List all deployed jobs"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, remote)
    user_auth = get_user_auth(client_config, lifecycle_url)

    r = Requests.get(
        f'{lifecycle_url}/api/v1/job',
        headers=get_auth_request_headers(user_auth),
    )
    jobs: List[Dict] = parse_response_list(r, 'Lifecycle response error')

    if not jobs:
        logger.info(f'No jobs deployed at {lifecycle_url}.')
        return

    header = ['NAME', 'VERSION', 'STATUS']
    if JobTableColumn.infrastructure in columns or JobTableColumn.all in columns:
        header.append('INFRASTRUCTURE')
    if JobTableColumn.deployed_by in columns or JobTableColumn.all in columns:
        header.append('DEPLOYED BY')
    if JobTableColumn.updated_at in columns or JobTableColumn.all in columns:
        header.append('UPDATED AT')
    if JobTableColumn.last_call_at in columns or JobTableColumn.all in columns:
        header.append('LAST CALL AT')
    if JobTableColumn.pub_url in columns or JobTableColumn.all in columns:
        header.append('PUB URL')

    table: List[List[str]] = [header]
    for job in jobs:
        name = job.get('name')
        version = job.get('version')
        status = job.get('status', '').upper()
        cells = [name, version, status]

        if JobTableColumn.infrastructure in columns or JobTableColumn.all in columns:
            cells.append(job.get('infrastructure_target'))
        if JobTableColumn.deployed_by in columns or JobTableColumn.all in columns:
            cells.append(job.get('deployed_by'))
        if JobTableColumn.updated_at in columns or JobTableColumn.all in columns:
            update_time = job.get('update_time')
            updated_ago = nullable_timestamp_pretty_ago(update_time)
            cells.append(updated_ago)
        if JobTableColumn.last_call_at in columns or JobTableColumn.all in columns:
            last_call_time = job.get('last_call_time')
            last_call_ago = nullable_timestamp_pretty_ago(last_call_time)
            cells.append(last_call_ago)
        if JobTableColumn.pub_url in columns or JobTableColumn.all in columns:
            cells.append(job.get('pub_url'))

        table.append(cells)

    logger.info(f'List of all jobs ({len(jobs)}) deployed at {lifecycle_url}:')
    print_table(table)


def move_job(remote: Optional[str], job_name: str, job_version: str, new_infra_target: str):
    """Move job from one infrastructure target to another"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, remote)
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


def delete_job(name: str, version: str, remote: Optional[str]):
    """Delete versioned job instance"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, remote)
    user_auth = get_user_auth(client_config, lifecycle_url)

    logger.debug(f'Deleting job "{name}" v{version} from {lifecycle_url}...')
    r = Requests.delete(
        f'{lifecycle_url}/api/v1/job/{name}/{version}',
        headers=get_auth_request_headers(user_auth),
    )
    parse_response(r, 'Lifecycle response error')
    logger.info(f'Job "{name}" v{version} has been deleted from {lifecycle_url}')
