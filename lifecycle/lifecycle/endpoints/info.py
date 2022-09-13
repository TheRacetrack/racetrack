from typing import List, Optional
from urllib.parse import urlsplit
import os

from fastapi import APIRouter

from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.config import Config
from racetrack_commons.plugin.plugin_manifest import PluginManifest


def setup_info_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):

    @api.get('/info')
    async def _info():
        """Report current configuration status"""
        return {
            'service': 'lifecycle',
            'git_version': os.environ.get('GIT_VERSION', 'dev'),
            'docker_tag': os.environ.get('DOCKER_TAG', ''),
            'auth_required': config.auth_required,
        }

    @api.get('/info/plugins', response_model=List[PluginManifest])
    def _info_plugins():
        """Get List of loaded plugins with their versions"""
        return plugin_engine.plugin_manifests

    @api.get('/info/plugin/{plugin_name}/docs', response_model=Optional[str])
    def _info_plugin_docs(plugin_name: str):
        """Get documentation for this plugin in markdown format"""
        return plugin_engine.invoke_one_plugin_hook(plugin_name, PluginCore.markdown_docs)


def _hide_url_credentials(remote: str) -> str:
    """Hide credentials from git remote url"""
    url = urlsplit(remote)
    if url.username or url.password:
        if url.port:
            return f'{url.scheme}://{url.hostname}:{url.port}{url.path}'
        else:
            return f'{url.scheme}://{url.hostname}{url.path}'
    return remote
