from typing import List, Optional
import os

from fastapi import APIRouter, UploadFile, Request

from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.config import Config
from racetrack_commons.plugin.plugin_manifest import PluginManifest
from lifecycle.auth.check import check_auth
from racetrack_commons.auth.auth import AuthSubjectType


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

    @api.get('/plugins', response_model=List[PluginManifest])
    def _info_plugins():
        """Get List of loaded plugins with their versions"""
        return plugin_engine.plugin_manifests

    @api.post('/plugin/upload')
    def _upload_plugin(file: UploadFile, request: Request):
        """Upload plugin from ZIP file and activate it"""
        check_auth(request, subject_types=[AuthSubjectType.USER])
        file_bytes = file.file.read()
        plugin_engine.upload_plugin(file.filename, file_bytes)
    
    @api.delete('/plugin/{plugin_name}')
    def _delete_plugin(plugin_name: str, request: Request):
        """Deactivate plugin"""
        check_auth(request, subject_types=[AuthSubjectType.USER])
        plugin_engine.delete_plugin(plugin_name)

    @api.get('/plugin/{plugin_name}/docs', response_model=Optional[str])
    def _info_plugin_docs(plugin_name: str):
        """Get documentation for this plugin in markdown format"""
        return plugin_engine.invoke_one_plugin_hook(plugin_name, PluginCore.markdown_docs)
