import asyncio
import collections
from typing import List, Optional, Any

from pydantic import BaseModel, Field
from fastapi import APIRouter, UploadFile, Request

from lifecycle.server.cache import LifecycleCache
from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.config import Config
from lifecycle.infrastructure.infra_target import list_infrastructure_names_with_origins
from lifecycle.auth.check import check_staff_user


class PluginUpdate(BaseModel):
    config_data: str = Field(description='text content of configuration file')


class PluginInfrastructureGroup(BaseModel):
    kind: str
    instances: list[str]


def setup_plugin_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):

    @api.get('/plugin', response_model=List[PluginManifest])
    def _info_plugins() -> List[PluginManifest]:
        """Get List of loaded plugins with their versions"""
        return plugin_engine.plugin_manifests

    @api.post('/plugin/upload')
    def _upload_plugin(file: UploadFile, request: Request, replace: int = 0):
        """Upload plugin from ZIP file using multipart/form-data"""
        check_staff_user(request)
        file_bytes = file.file.read()
        plugin_engine.upload_plugin(file.filename, file_bytes, bool(replace))

    @api.post('/plugin/upload/{filename}')
    async def _upload_plugin_bytes(filename: str, request: Request, replace: int = 0) -> PluginManifest:
        """Upload plugin from ZIP file sending raw bytes in body"""
        check_staff_user(request)
        file_bytes: bytes = await request.body()
        loop = asyncio.get_running_loop()
        # Run synchronous function asynchronously without blocking an event loop, using default ThreadPoolExecutor
        return await loop.run_in_executor(None, plugin_engine.upload_plugin, filename, file_bytes, bool(replace))
    
    @api.delete('/plugin/{plugin_name}/{plugin_version}')
    def _delete_plugin_by_version(plugin_name: str, plugin_version: str, request: Request):
        """Deactivate and remove plugin with given name and version"""
        check_staff_user(request)
        plugin_engine.delete_plugin_by_version(plugin_name, plugin_version)

    @api.delete('/plugin/all')
    def _delete_all_plugins(request: Request):
        """Deactivate and remove all plugins"""
        check_staff_user(request)
        plugin_engine.delete_all_plugins()

    @api.get('/plugin/{plugin_name}/{plugin_version}/config')
    def _read_plugin_config(plugin_name: str, plugin_version: str, request: Request) -> str:
        """Read plugin's configuration"""
        check_staff_user(request)
        return plugin_engine.read_plugin_config(plugin_name, plugin_version)

    @api.put('/plugin/{plugin_name}/{plugin_version}/config')
    def _write_plugin_config(payload: PluginUpdate, plugin_name: str, plugin_version: str, request: Request):
        """Update plugin's configuration"""
        check_staff_user(request)
        plugin_engine.write_plugin_config(plugin_name, plugin_version, payload.config_data)

    @api.get('/plugin/{plugin_name}/docs')
    def _info_plugin_docs(plugin_name: str) -> Optional[str]:
        """Get documentation for this plugin in Markdown format"""
        return plugin_engine.invoke_one_plugin_hook(plugin_name, PluginCore.markdown_docs)

    @api.post('/plugin/{plugin_name}/run')
    def _run_plugin_action(plugin_name: str, payload_params: dict[str, Any], request: Request) -> Any:
        """Call a supplementary action of a plugin"""
        params = dict(request.query_params)
        params.update(payload_params)
        return plugin_engine.invoke_one_plugin_hook(plugin_name, PluginCore.run_action, **params)

    @api.get('/plugin/job_type/versions')
    def _get_job_type_versions() -> list[str]:
        """List available job type versions"""
        return sorted(LifecycleCache.job_types.keys())

    @api.get('/plugin/infrastructure_targets')
    def _get_infrastructure_targets() -> dict[str, PluginManifest]:
        """Return names of available infrastructure targets mapped to the plugin of origin"""
        return list_infrastructure_names_with_origins(plugin_engine)

    @api.get('/plugin/tree')
    def _get_plugin_trees() -> dict:
        infrastructure_targets: dict[str, PluginManifest] = list_infrastructure_names_with_origins(plugin_engine)
        plugins: list[PluginManifest] = plugin_engine.plugin_manifests
        job_type_versions: list[str] = sorted(LifecycleCache.job_types.keys())

        # Collect instances running on the same infrastructure
        _infrastructure_instances: dict[str, list[str]] = collections.defaultdict(list)
        for infrastructure_name, plugin_manifest in infrastructure_targets.items():
            _infrastructure_instances[plugin_manifest.name].append(infrastructure_name)
        infrastructure_instances: list[PluginInfrastructureGroup] = [
            PluginInfrastructureGroup(kind=k, instances=v)
            for k, v in _infrastructure_instances.items()
        ]

        return {
            'plugins': plugins,
            'job_type_versions': job_type_versions,
            'infrastructure_targets': infrastructure_targets,
            'infrastructure_instances': sorted(infrastructure_instances, key=lambda i: i.kind),
        }
