import asyncio
import collections
from typing import List, Optional, Any

from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Response, UploadFile, Request

from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_commons.deploy.job_type import list_jobtype_names_of_plugins
from racetrack_commons.entities.audit import AuditLogEventType
from racetrack_commons.plugin.core import PluginCore
from racetrack_commons.plugin.engine import PluginEngine
from lifecycle.django.registry import models
from lifecycle.job import models_registry
from lifecycle.auth.authenticate import get_username_from_token
from lifecycle.job.audit import AuditLogger
from lifecycle.server.cache import LifecycleCache
from lifecycle.infrastructure.infra_target import list_infrastructure_names_with_origins, \
    list_infrastructure_names_of_plugins
from lifecycle.auth.check import check_staff_user


class PluginUpdate(BaseModel):
    config_data: str = Field(description='text content of configuration file')


class JobTypeData(BaseModel):
    name: str
    active_jobs: int


class JobTypePluginData(BaseModel):
    name: str
    version: str
    job_types: list[JobTypeData]


class InfrastructureData(BaseModel):
    name: str
    active_jobs: int


class InfrastructurePluginData(BaseModel):
    name: str
    version: str
    infrastructures: list[InfrastructureData]


class PluginsData(BaseModel):
    plugins: list[PluginManifest]
    job_type_plugins_data: list[JobTypePluginData]
    infrastructure_plugins_data: list[InfrastructurePluginData]


def setup_plugin_endpoints(api: APIRouter, plugin_engine: PluginEngine):
    @api.get('/plugin/{plugin_name}/{plugin_version}/download')
    def _download_installed_plugin_version(plugin_name: str, plugin_version: str) -> Response:
        plugin_path = plugin_engine.plugins_path / f"{plugin_name}-{plugin_version}.zip"
        if not plugin_path.exists():
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' version '{plugin_version}' not found")

        return FileResponse(plugin_path, media_type='application/zip', filename=plugin_path.name)

    @api.get('/plugin', response_model=List[PluginManifest])
    def _info_plugins() -> List[PluginManifest]:
        """Get List of loaded plugins with their versions"""
        return plugin_engine.plugin_manifests

    @api.post('/plugin/upload')
    def _upload_plugin(file: UploadFile, request: Request, replace: int = 0):
        """Upload plugin from ZIP file using multipart/form-data"""
        check_staff_user(request)
        username = get_username_from_token(request)
        file_bytes = file.file.read()
        manifest = plugin_engine.upload_plugin(file.filename, file_bytes, bool(replace))
        log_event_plugin_installed(manifest.name, manifest.version, username)

    @api.post('/plugin/upload/{filename}')
    async def _upload_plugin_bytes(filename: str, request: Request, replace: int = 0) -> PluginManifest:
        """Upload plugin from ZIP file sending raw bytes in body"""
        check_staff_user(request)
        username = get_username_from_token(request)
        file_bytes: bytes = await request.body()
        loop = asyncio.get_running_loop()
        # Run synchronous function asynchronously without blocking an event loop, using default ThreadPoolExecutor
        manifest = await loop.run_in_executor(None, plugin_engine.upload_plugin, filename, file_bytes, bool(replace))
        log_event_plugin_installed(manifest.name, manifest.version, username)
        return manifest

    @api.delete('/plugin/{plugin_name}/{plugin_version}')
    def _delete_plugin_by_version(plugin_name: str, plugin_version: str, request: Request):
        """Deactivate and remove plugin with given name and version"""
        check_staff_user(request)
        username = get_username_from_token(request)
        plugin_engine.delete_plugin_by_version(plugin_name, plugin_version)
        log_event_plugin_uninstalled(plugin_name, plugin_version, username)

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
        check_staff_user(request)
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
    def _get_plugin_trees() -> PluginsData:
        return _get_plugins_data(plugin_engine)


def _get_plugins_data(plugin_engine: PluginEngine) -> PluginsData:
    job_models: list[models.Job] = list(models_registry.list_job_models())
    jobtypes_usage: dict[str, int] = collections.defaultdict(int)
    infrastructure_usage: dict[str, int] = collections.defaultdict(int)
    for job_model in job_models:
        jobtypes_usage[job_model.job_type_version] += 1
        if job_model.infrastructure_target:
            infrastructure_usage[job_model.infrastructure_target] += 1

    jobtype_names_by_plugins: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for plugin, jobtype_name in list_jobtype_names_of_plugins(plugin_engine):
        jobtype_names_by_plugins[(plugin.name, plugin.version)].append(jobtype_name)

    job_type_plugins_data: list[JobTypePluginData] = []
    for plugin_tuple, jobtype_names in jobtype_names_by_plugins.items():
        job_types_data: list[JobTypeData] = [JobTypeData(name=name, active_jobs=jobtypes_usage[name]) for name in jobtype_names]
        job_type_plugins_data.append(JobTypePluginData(
            name=plugin_tuple[0],
            version=plugin_tuple[1],
            job_types=job_types_data,
        ))

    infrastructure_names_by_plugins: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for plugin, infrastructure_name in list_infrastructure_names_of_plugins(plugin_engine):
        infrastructure_names_by_plugins[(plugin.name, plugin.version)].append(infrastructure_name)

    infrastructure_plugins_data: list[InfrastructurePluginData] = []
    for plugin_tuple, infrastructure_names in infrastructure_names_by_plugins.items():
        infrastructures_data: list[InfrastructureData] = [InfrastructureData(name=name, active_jobs=infrastructure_usage[name]) for name in infrastructure_names]
        infrastructure_plugins_data.append(InfrastructurePluginData(
            name=plugin_tuple[0],
            version=plugin_tuple[1],
            infrastructures=infrastructures_data,
        ))

    return PluginsData(
        plugins=plugin_engine.plugin_manifests,
        job_type_plugins_data=sorted(job_type_plugins_data, key=lambda x: (x.name, x.version)),
        infrastructure_plugins_data=sorted(infrastructure_plugins_data, key=lambda x: (x.name, x.version)),
    )


def log_event_plugin_installed(plugin_name: str, plugin_version: str, username: str):
    AuditLogger().log_event(
        AuditLogEventType.PLUGIN_INSTALLED,
        username_executor=username,
        properties={
            'plugin_name': plugin_name,
            'plugin_version': plugin_version,
        },
    )


def log_event_plugin_uninstalled(plugin_name: str, plugin_version: str, username: str):
    AuditLogger().log_event(
        AuditLogEventType.PLUGIN_UNINSTALLED,
        username_executor=username,
        properties={
            'plugin_name': plugin_name,
            'plugin_version': plugin_version,
        },
    )
