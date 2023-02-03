from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from racetrack_client.client_config.alias import resolve_lifecycle_url
from racetrack_client.client_config.auth import get_user_auth
from racetrack_client.client_config.client_config import ClientConfig
from racetrack_client.client_config.io import load_client_config
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.auth import get_auth_request_headers
from racetrack_client.utils.request import parse_response, parse_response_object, parse_response_list, Requests
from racetrack_client.utils.semver import SemanticVersion

logger = get_logger(__name__)


def install_plugin(
    plugin_uri: str,
    lifecycle_url: Optional[str],
    client_config: Optional[ClientConfig] = None,
):
    """Install a plugin to a remote Racetrack server"""
    if client_config is None:
        client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)

    plugin_filename, plugin_content = _load_plugin_file(plugin_uri)

    logger.info(f'Uploading plugin {plugin_uri} to {lifecycle_url}')
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
    lifecycle_url: Optional[str],
):
    """Uninstall plugin from a remote Racetrack server"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)

    logger.info(f'Uninstalling plugin {plugin_name} {plugin_version} from {lifecycle_url}')
    r = Requests.delete(
        f'{lifecycle_url}/api/v1/plugin/{plugin_name}/{plugin_version}',
        headers=get_auth_request_headers(user_auth),
    )
    parse_response(r, 'Lifecycle response error')

    logger.info(f'Plugin {plugin_name} {plugin_version} has been uninstalled from {lifecycle_url}')


def list_installed_plugins(lifecycle_url: Optional[str]) -> None:
    """List plugins installed on a remote Racetrack server"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)

    r = Requests.get(
        f'{lifecycle_url}/api/v1/plugin',
        headers=get_auth_request_headers(user_auth),
    )
    plugin_manifests: List[Dict] = parse_response_list(r, 'Lifecycle response error')
    plugin_infos = [f'{p["name"]}=={p["version"]}' for p in plugin_manifests]

    logger.info(f'Plugins currently installed on {lifecycle_url} ({len(plugin_infos)}):')
    for info in plugin_infos:
        print(info)


def list_available_job_types(lifecycle_url: Optional[str]) -> None:
    """List job type versions available on a remote Racetrack server"""
    client_config = load_client_config()
    lifecycle_url = resolve_lifecycle_url(client_config, lifecycle_url)
    user_auth = get_user_auth(client_config, lifecycle_url)

    r = Requests.get(
        f'{lifecycle_url}/api/v1/plugin/job_type/versions',
        headers=get_auth_request_headers(user_auth),
    )
    versions: List[str] = parse_response_list(r, 'Lifecycle response error')

    logger.info(f'Job type versions currently installed on {lifecycle_url} ({len(versions)}):')
    for version in versions:
        print(version)


def _load_plugin_file(plugin_uri: str) -> Tuple[str, bytes]:
    local_file = Path(plugin_uri)
    if local_file.is_file():
        logger.debug(f'{plugin_uri} recognized as a local file')
        file_content = local_file.read_bytes()
        return local_file.name, file_content

    if plugin_uri.startswith('http') and plugin_uri.endswith('.zip'):
        logger.debug(f'{plugin_uri} recognized as a remote HTTP file')
        return download_file(plugin_uri)

    if plugin_uri.startswith('github.com/'):
        if '==' in plugin_uri:
            logger.debug(f'{plugin_uri} recognized as a specific version of a GitHub repository')
            parts = plugin_uri.split('==')
            return _get_github_release(parts[0], parts[1])
        else:
            logger.debug(f'{plugin_uri} recognized as a GitHub repository')
            return _get_latest_github_release(plugin_uri)

    raise ValueError(f'Unknown plugin location: {plugin_uri}')


def download_file(url: str) -> Tuple[str, bytes]:
    logger.info(f'downloading file {url}')
    filename = Path(urlparse(url).path).name
    response = Requests.get(url)
    response.raise_for_status()
    logger.debug(f'file {filename} downloaded ({len(response.content)} bytes)')
    return filename, response.content


@dataclass
class PluginRelease:
    version: str
    download_url: str


def _get_latest_github_release(repo_name: str) -> Tuple[str, bytes]:
    releases = _list_github_releases(repo_name)
    assert releases, f'repository {repo_name} doesn\'t have any valid release'
    latest_release = releases[-1]
    logger.info(f'getting latest version {latest_release.version} from the {repo_name} repository')
    return download_file(latest_release.download_url)


def _get_github_release(repo_name: str, version: str) -> Tuple[str, bytes]:
    releases = _list_github_releases(repo_name)
    assert releases, f'repository {repo_name} doesn\'t have any valid release'
    filtered_releases = [r for r in releases if r.version == version]
    assert filtered_releases, f'repository {repo_name} doesn\'t have a release with version {version}'
    release = filtered_releases[0]
    logger.info(f'getting version {release.version} from the {repo_name} repository')
    return download_file(release.download_url)


def _list_github_releases(repo_name: str) -> List[PluginRelease]:
    match = re.fullmatch(r'github.com/(.+)/(.+)', repo_name)
    assert match, f'can\'t match repo {repo_name} to a pattern'
    gh_user = match.group(1)
    gh_repo = match.group(2)

    headers = {
        'User-Agent': 'racetrack-client',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if github_token := os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = f'Bearer {github_token}'

    r = Requests.get(
        f'https://api.github.com/repos/{gh_user}/{gh_repo}/releases',
        headers=headers,
    )

    json_releases = parse_response_list(r, 'GitHub API response')
    releases = []
    for json_release in json_releases:
        version = json_release.get('tag_name')
        if not version:
            version = json_release.get('name')
        zip_assets = [asset['browser_download_url']
                      for asset in json_release['assets']
                      if asset['browser_download_url'].endswith('.zip')]
        if version and zip_assets:
            releases.append(PluginRelease(version, zip_assets[0]))

    releases.sort(key=lambda r: SemanticVersion(r.version))
    return releases
