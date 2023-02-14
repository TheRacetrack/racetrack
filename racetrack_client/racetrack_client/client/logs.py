from typing import Optional

from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.client.socketio import LogsConsumer
from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.request import parse_response_object, Requests

logger = get_logger(__name__)


def show_runtime_logs(name: str, version: str, remote: Optional[str], tail: int, follow: bool):
    """
    Show logs from job output
    :param workdir: directory with job.yaml manifest
    :param lifecycle_url: URL to Lifecycle API
    :param tail: number of recent lines to show
    :param follow: whether to follow logs output stream
    """
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, remote)
    user_auth = get_user_auth(client_config, lifecycle_url)
    logger.info(f'Retrieving runtime logs of job "{name}" v{version} from {lifecycle_url}...')

    if follow:
        _show_runtime_logs_following(lifecycle_url, name, version, tail)
    else:
        _show_runtime_logs_once(lifecycle_url, name, version, tail, user_auth)


def _show_runtime_logs_once(lifecycle_url: str, name: str, version: str, tail: int, user_auth: str):
    r = Requests.get(
        f'{lifecycle_url}/api/v1/job/{name}/{version}/logs',
        params={'tail': tail},
        headers=get_auth_request_headers(user_auth),
    )
    response = parse_response_object(r, 'Lifecycle response error')
    logs: str = response['logs']
    log_lines = len(logs.splitlines())
    logger.info(f'Viewing the latest logs from job "{name}" v{version} below'
                f' ({log_lines} lines):\n---')
    print(logs)


def _show_runtime_logs_following(lifecycle_url: str, name: str, version: str, tail: int):
    def on_next_line(line: str):
        print(line.strip())

    resource_properties = {
        'job_name': name,
        'job_version': version,
        'tail': str(tail),
    }
    consumer = LogsConsumer(lifecycle_url, 'lifecycle/socket.io', resource_properties, on_next_line)
    logger.info(f'Streaming live logs from job "{name}" v{version} below:\n---')
    consumer.connect_and_wait()


def show_build_logs(name: str, version: str, remote: Optional[str], tail: int = 0):
    """
    Show output of latest job image building process
    :param workdir: directory with job.yaml manifest
    :param lifecycle_url: URL to Lifecycle API
    :param tail: number of recent lines to show. If zero, all logs are displayed.
    """
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, remote)
    user_auth = get_user_auth(client_config, lifecycle_url)
    logger.info(f'Retrieving build logs of job "{name}" v{version} from {lifecycle_url}...')

    r = Requests.get(
        f'{lifecycle_url}/api/v1/job/{name}/{version}/build-logs',
        params={'tail': tail},
        headers=get_auth_request_headers(user_auth),
    )
    response = parse_response_object(r, 'Lifecycle response error')
    logs: str = response['logs']
    log_lines = len(logs.splitlines())
    logger.info(f'Recent build logs of "{name}" job ({log_lines} lines):\n')
    print(logs)
