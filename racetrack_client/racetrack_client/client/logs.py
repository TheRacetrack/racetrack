from typing import Optional

from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.client.socketio import LogsConsumer
from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.manifest import Manifest
from racetrack_client.manifest.validate import load_validated_manifest
from racetrack_client.utils.request import parse_response_object, Requests

logger = get_logger(__name__)


def show_runtime_logs(workdir: str, lifecycle_url: Optional[str], tail: int, follow: bool):
    """
    Show logs from fatman output
    :param workdir: directory with fatman.yaml manifest
    :param lifecycle_url: URL to Lifecycle API
    :param tail: number of recent lines to show
    :param follow: whether to follow logs output stream
    """
    client_config = load_client_config()
    manifest = load_validated_manifest(workdir)
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)
    logger.info(f'Retrieving runtime logs of fatman "{manifest.name}" v{manifest.version} from {lifecycle_url}...')

    if follow:
        _show_runtime_logs_following(lifecycle_url, manifest, tail)
    else:
        _show_runtime_logs_once(lifecycle_url, manifest, tail, user_auth)


def _show_runtime_logs_once(lifecycle_url: str, manifest: Manifest, tail: int, user_auth: str):
    r = Requests.get(
        f'{lifecycle_url}/api/v1/fatman/{manifest.name}/{manifest.version}/logs',
        params={'tail': tail},
        headers=get_auth_request_headers(user_auth),
    )
    response = parse_response_object(r, 'Lifecycle response error')
    logs: str = response['logs']
    log_lines = len(logs.splitlines())
    logger.info(f'Viewing the latest logs from fatman "{manifest.name}" v{manifest.version} below'
                f' ({log_lines} lines):\n---')
    print(logs)


def _show_runtime_logs_following(lifecycle_url: str, manifest: Manifest, tail: int):
    def on_next_line(line: str):
        print(line.strip())

    resource_properties = {
        'fatman_name': manifest.name,
        'fatman_version': manifest.version,
        'tail': str(tail),
    }
    consumer = LogsConsumer(lifecycle_url, 'lifecycle/socket.io', resource_properties, on_next_line)
    logger.info(f'Streaming live logs from fatman "{manifest.name}" v{manifest.version} below:\n---')
    consumer.connect_and_wait()


def show_build_logs(workdir: str, lifecycle_url: Optional[str], tail: int = 0):
    """
    Show output of latest fatman image building process
    :param workdir: directory with fatman.yaml manifest
    :param lifecycle_url: URL to Lifecycle API
    :param tail: number of recent lines to show. If zero, all logs are displayed.
    """
    client_config = load_client_config()
    manifest = load_validated_manifest(workdir)
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)
    logger.info(f'Retrieving build logs of fatman "{manifest.name}" v{manifest.version} from {lifecycle_url}...')

    r = Requests.get(
        f'{lifecycle_url}/api/v1/fatman/{manifest.name}/{manifest.version}/build-logs',
        params={'tail': tail},
        headers=get_auth_request_headers(user_auth),
    )
    response = parse_response_object(r, 'Lifecycle response error')
    logs: str = response['logs']
    log_lines = len(logs.splitlines())
    logger.info(f'Recent build logs of "{manifest.name}" fatman ({log_lines} lines):\n')
    print(logs)
