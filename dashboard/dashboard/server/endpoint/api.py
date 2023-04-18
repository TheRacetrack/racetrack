from __future__ import annotations
import asyncio
import collections
import os

from fastapi import Request, FastAPI, Response
from racetrack_client.plugin.plugin_manifest import PluginManifest
from racetrack_client.utils.time import days_ago
from racetrack_commons.entities.audit import explain_audit_log_event
from racetrack_commons.entities.audit_client import AuditClient
from racetrack_commons.entities.dto import AuditLogEventDto, JobDto
from racetrack_commons.entities.job_client import JobRegistryClient
from racetrack_commons.entities.plugin_client import LifecyclePluginClient
from racetrack_commons.urls import get_external_lifecycle_url, get_external_pub_url
from dashboard.purge import enrich_jobs_purge_info
from dashboard.utils import remove_ansi_sequences
from dashboard.server.endpoint.account import get_auth_token, setup_account_endpoints


def setup_api_endpoints(app: FastAPI):

    setup_account_endpoints(app)

    @app.get("/api/status")
    def _status():
        """Report current application status"""
        site_name = os.environ.get('SITE_NAME', '')
        return {
            'service': 'dashboard',
            'live': True,
            'ready': True,
            'git_version': os.environ.get('GIT_VERSION', 'dev'),
            'docker_tag': os.environ.get('DOCKER_TAG', ''),
            'lifecycle_url': get_external_lifecycle_url(),
            'external_pub_url': get_external_pub_url(),
            'site_name': site_name,
        }

    @app.get("/api/job/list")
    def jobs_list(request: Request) -> dict:
        jobs_client = _get_job_registry_client(request)
        return {
            'external_pub_url': get_external_pub_url(),
            'jobs': jobs_client.list_deployed_jobs(),
        }
    
    @app.get("/api/job/graph")
    def jobs_graph(request: Request) -> dict:
        jobs_client = _get_job_registry_client(request)
        return {
            'job_graph': jobs_client.get_dependencies_graph(),
        }
    
    @app.get("/api/job/portfolio")
    def jobs_portfolio(request: Request) -> dict:
        jobs_client = _get_job_registry_client(request)
        
        jobs: list[JobDto] = jobs_client.list_deployed_jobs()
        job_dicts: list[dict] = enrich_jobs_purge_info(jobs)

        for job_dict in job_dicts:
            job_dict['update_time_days_ago'] = days_ago(job_dict['update_time'])
            job_dict['last_call_time_days_ago'] = days_ago(job_dict['last_call_time'])

        return {
            'external_pub_url': get_external_pub_url(),
            'jobs': job_dicts,
        }
    
    @app.get("/api/job/activity")
    def jobs_activity(request: Request, job_name: str = '', job_version: str = '', related_to_me: str = '') -> dict:
        audit_client = AuditClient(auth_token=get_auth_token(request))
        filter_related_to_me: bool = related_to_me.lower() in {'true', 'yes', '1'}
            
        events: list[AuditLogEventDto] = audit_client.filter_events(filter_related_to_me, job_name, job_version)

        event_dicts = []
        for event in events:
            event_dict = event.dict()
            event_dict['explanation'] = explain_audit_log_event(event)
            event_dicts.append(event_dict)

        return {
            'filter_job_name': job_name,
            'filter_job_version': job_version,
            'filter_related_to_me': filter_related_to_me,
            'events': event_dicts,
        }

    @app.delete("/api/job/{job_name}/{job_version}")
    def delete_job(request: Request, job_name: str, job_version: str):
        jobs_client = _get_job_registry_client(request)
        jobs_client.delete_deployed_job(job_name, job_version)
        return Response(status_code=204)

    @app.post("/api/job/{job_name}/{job_version}/redeploy")
    def redeploy_job(request: Request, job_name: str, job_version: str):
        jobs_client = _get_job_registry_client(request)
        jobs_client.redeploy_job(job_name, job_version)

    @app.post("/api/job/{job_name}/{job_version}/reprovision")
    def reprovision_job(request: Request, job_name: str, job_version: str):
        jobs_client = _get_job_registry_client(request)
        jobs_client.reprovision_job(job_name, job_version)

    @app.get("/api/job/{job_name}/{job_version}/runtime-logs")
    def job_runtime_logs(request: Request, job_name: str, job_version: str, tail: int = 0):
        content = _get_job_registry_client(request).get_runtime_logs(job_name, job_version, tail)
        content = remove_ansi_sequences(content)
        return Response(content, media_type='text/plain; charset=utf-8')

    @app.get("/api/job/{job_name}/{job_version}/build-logs")
    def job_build_logs(request: Request, job_name: str, job_version: str, tail: int = 0):
        content = _get_job_registry_client(request).get_build_logs(job_name, job_version, tail)
        content = remove_ansi_sequences(content)
        return Response(content, media_type='text/plain; charset=utf-8')

    @app.get("/api/administration")
    def get_administration(request: Request) -> dict:
        plugin_client = LifecyclePluginClient()
        infrastructure_targets: dict[str, PluginManifest] = plugin_client.get_infrastructure_targets()

        # Collect instances running on the same infrastructure
        _infrastructure_instances: dict[str, list[str]] = collections.defaultdict(list)
        for infrastructure_name, plugin_manifest in infrastructure_targets.items():
            _infrastructure_instances[plugin_manifest.name].append(infrastructure_name)
        infrastructure_instances: list[tuple[str, list[str]]] = sorted(_infrastructure_instances.items())

        return {
            'plugins': plugin_client.get_plugins_info(),
            'job_type_versions': plugin_client.get_job_type_versions(),
            'infrastructure_targets': infrastructure_targets,
            'infrastructure_instances': infrastructure_instances,
        }
    

    @app.get("/api/plugin/{plugin_name}/{plugin_version}")
    def get_plugin_config(request: Request, plugin_name: str, plugin_version: str) -> dict:
        plugin_client = LifecyclePluginClient(auth_token=get_auth_token(request))
        return {
            'plugin_name': plugin_name,
            'plugin_version': plugin_version,
            'plugin_config': plugin_client.read_plugin_config(plugin_name, plugin_version),
        }

    @app.delete("/api/plugin/{plugin_name}/{plugin_version}")
    def delete_plugin(request: Request, plugin_name: str, plugin_version: str):
        client = LifecyclePluginClient(auth_token=get_auth_token(request))
        client.delete_plugin(plugin_name, plugin_version)
        return Response(status_code=204)

    @app.post("/api/plugin/{plugin_name}/{plugin_version}/config")
    def save_plugin_config(request: Request, plugin_name: str, plugin_version: str, payload: str):
        client = LifecyclePluginClient(auth_token=get_auth_token(request))
        client.write_plugin_config(plugin_name, plugin_version, payload)

    @app.post('/plugin/upload/{filename}')
    async def _upload_plugin(filename: str, request: Request):
        """Upload plugin from ZIP file sending raw bytes in body"""
        client = LifecyclePluginClient(auth_token=get_auth_token(request))
        file_bytes: bytes = await request.body()
        loop = asyncio.get_running_loop()

        def _upload():
            client.upload_plugin(filename, file_bytes)

        # Run synchronous function asynchronously without blocking an event loop, using default ThreadPoolExecutor
        await loop.run_in_executor(None, _upload)
    

def _get_job_registry_client(request: Request) -> JobRegistryClient:
    return JobRegistryClient(auth_token=get_auth_token(request))
