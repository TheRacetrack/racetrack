from __future__ import annotations
import asyncio
from typing import List, Optional

from pydantic import BaseModel, Field
from fastapi import APIRouter, UploadFile, Request

from racetrack_client.utils.request import Requests, parse_response_list
from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.config import Config
from lifecycle.deployer.infra_target import list_infrastructure_names_with_origins
from lifecycle.auth.check import check_staff_user


class PluginUpdate(BaseModel):
    config_data: str = Field(description='text content of configuration file')


def setup_plugin_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):

    @api.get('/plugin', response_model=List[PluginManifest])
    def _info_plugins() -> List[PluginManifest]:
        """Get List of loaded plugins with their versions"""
        return plugin_engine.plugin_manifests

    @api.post('/plugin/upload')
    def _upload_plugin(file: UploadFile, request: Request):
        """Upload plugin from ZIP file using multipart/form-data"""
        check_staff_user(request)
        file_bytes = file.file.read()
        plugin_engine.upload_plugin(file.filename, file_bytes)

    @api.post('/plugin/upload/{filename}')
    async def _upload_plugin_bytes(filename: str, request: Request) -> PluginManifest:
        """Upload plugin from ZIP file sending raw bytes in body"""
        check_staff_user(request)
        file_bytes: bytes = await request.body()
        loop = asyncio.get_running_loop()
        # Run synchronous function asynchronously without blocking an event loop, using default ThreadPoolExecutor
        return await loop.run_in_executor(None, plugin_engine.upload_plugin, filename, file_bytes)
    
    @api.delete('/plugin/{plugin_name}/{plugin_version}')
    def _delete_plugin_by_version(plugin_name: str, plugin_version: str, request: Request):
        """Deactivate and remove plugin with given name and version"""
        check_staff_user(request)
        plugin_engine.delete_plugin_by_version(plugin_name, plugin_version)

    @api.get('/plugin/{plugin_name}/{plugin_version}/config')
    def _read_plugin_config(plugin_name: str, plugin_version: str, request: Request) -> str:
        """Read plugin's configuration"""
        check_staff_user(request)
        return plugin_engine.read_plugin_config(plugin_name, plugin_version)

    @api.put('/plugin/{plugin_name}/{plugin_version}/config')
    def _write_plugin_config(payload: PluginUpdate, plugin_name: str, plugin_version: str, request: Request) -> str:
        """Read plugin's configuration"""
        check_staff_user(request)
        return plugin_engine.write_plugin_config(plugin_name, plugin_version, payload.config_data)

    @api.get('/plugin/{plugin_name}/docs')
    def _info_plugin_docs(plugin_name: str) -> Optional[str]:
        """Get documentation for this plugin in markdown format"""
        return plugin_engine.invoke_one_plugin_hook(plugin_name, PluginCore.markdown_docs)

    @api.get('/plugin/job_type/versions')
    def _get_job_type_versions() -> list[str]:
        """List available job type versions"""
        r = Requests.get(f'{config.image_builder_url}/api/v1/job_type/versions')
        return parse_response_list(r, 'Image builder API error')

    @api.get('/plugin/infrastructure_targets')
    def _get_infrastructure_targets() -> dict[str, PluginManifest]:
        """Return names of available infrastructure targets mapped to the plugin of origin"""
        return list_infrastructure_names_with_origins(plugin_engine)
