from typing import List
from urllib.parse import urlsplit
import os

from fastapi import APIRouter

from racetrack_commons.entities.dto import PluginConfigDto
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine, PluginConfig
from lifecycle.config import Config


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

    @api.get('/info/plugins', response_model=List[PluginConfigDto])
    def _info_plugins():
        """Get List of loaded plugins with their versions"""
        return [plugin_config_to_dto(pc) for pc in plugin_engine.plugin_configs]

    @api.get('/info/plugin/{plugin_name}/docs', response_model=List[PluginConfigDto])
    def _info_plugin_docs(plugin_name: str):
        """Get documentation for this plugin in markdown format"""
        return plugin_engine.invoke_one_plugin_hook(plugin_name, PluginCore.markdown_docs)


def plugin_config_to_dto(plugin_config: PluginConfig) -> PluginConfigDto:
    return PluginConfigDto(
        name=plugin_config.name,
        git_remote=_hide_url_credentials(plugin_config.git_remote),
        git_ref=plugin_config.git_ref,
        git_directory=plugin_config.git_directory,
    )


def _hide_url_credentials(remote: str) -> str:
    """Hide credentials from git remote url"""
    url = urlsplit(remote)
    if url.username or url.password:
        if url.port:
            return f'{url.scheme}://{url.hostname}:{url.port}{url.path}'
        else:
            return f'{url.scheme}://{url.hostname}{url.path}'
    return remote
