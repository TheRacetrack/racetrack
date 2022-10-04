from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.request import parse_response, parse_response_object, Requests

logger = get_logger(__name__)


def install_plugin(
    plugin_uri: str,
    lifecycle_url: str,
):
    """Install a plugin to a remote Racetrack server"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)

    plugin_filename, plugin_content = _load_plugin_file(plugin_uri)

    logger.info(f'Uploading pluign {plugin_uri} to {lifecycle_url}...')
    r = Requests.post(
        f'{lifecycle_url}/api/v1/plugin/upload/{plugin_filename}',
        data=plugin_content,
        headers=get_auth_request_headers(user_auth),
    )
    plugin_manifest = parse_response_object(r, 'Lifecycle response error')
    plugin_name = plugin_manifest.get('name')
    plugin_version = plugin_manifest.get('version')

    logger.info(f'Plugin {plugin_name} {plugin_version} has been installed to {lifecycle_url}')


def uninstall_plugin(
    plugin_name: str,
    plugin_version: str,
    lifecycle_url: str,
):
    """Uninstall plugin from a remote Racetrack server"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)

    logger.info(f'Uninstalling pluign {plugin_name} {plugin_version} from {lifecycle_url}...')
    r = Requests.delete(
        f'{lifecycle_url}/api/v1/plugin/{plugin_name}/{plugin_version}',
        headers=get_auth_request_headers(user_auth),
    )
    parse_response(r, 'Lifecycle response error')

    logger.info(f'Plugin {plugin_name} {plugin_version} has been uninstalled from {lifecycle_url}')


def _load_plugin_file(plugin_uri: str) -> Tuple[str, bytes]:
    local_file = Path(plugin_uri)
    if local_file.is_file():
        file_content = local_file.read_bytes()
        return local_file.name, file_content

    return download_file(plugin_uri)


def download_file(url: str) -> Tuple[str, bytes]:
    logger.info(f'downloading file {url}')
    filename = Path(urlparse(url).path).name
    response = Requests.get(url)
    response.raise_for_status()
    logger.debug(f'file {filename} downloaded ({len(response.content)} bytes)')
    return filename, response.content
