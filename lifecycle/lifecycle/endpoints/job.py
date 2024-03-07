from typing import List

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from job.async_job_call import save_async_job_call
from job.async_call import get_async_job_call
from job.dto_converter import async_job_call_to_dto
from lifecycle.auth.check import check_auth
from lifecycle.config import Config
from lifecycle.config.maintenance import ensure_no_maintenance
from lifecycle.deployer.redeploy import redeploy_job, reprovision_job, move_job
from lifecycle.job.ansi import strip_ansi_colors
from lifecycle.job.graph import build_job_dependencies_graph
from lifecycle.job.models_registry import update_job_manifest
from lifecycle.job.portfolio import enrich_jobs_purge_info
from lifecycle.job.registry import (
    delete_job,
    list_job_families,
    list_job_registry,
    read_versioned_job,
)
from lifecycle.job.public_endpoints import read_active_job_public_endpoints
from lifecycle.job.logs import read_build_logs, read_runtime_logs
from lifecycle.auth.authenticate import get_username_from_token
from racetrack_client.utils.time import days_ago
from racetrack_commons.entities.dto import JobDto, JobFamilyDto, AsyncJobCallDto
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.auth.scope import AuthScope


def setup_job_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):

    class MoveJobPayload(BaseModel):
        infrastructure_target: str = Field(description='text content of configuration file')

    class UpdateManifestPayload(BaseModel):
        manifest_yaml: str = Field(description='Job manifest in YAML format')

    @api.get('/job')
    def _list_all_jobs(request: Request) -> List[JobDto]:
        """Get list of deployed Jobs"""
        auth_subject = check_auth(request, scope=AuthScope.READ_JOB)
        return list_job_registry(config, auth_subject)

    @api.get('/job_family')
    def _get_job_family(request: Request) -> List[JobFamilyDto]:
        """Get list of deployed Job Families (names regardless version)"""
        auth_subject = check_auth(request, scope=AuthScope.READ_JOB)
        return list_job_families(auth_subject)

    @api.get('/job/graph')
    def _get_job_graph(request: Request):
        """Get Job dependencies graph"""
        auth_subject = check_auth(request, scope=AuthScope.READ_JOB)
        return build_job_dependencies_graph(config, auth_subject)

    @api.get('/job/portfolio')
    def _get_job_portfolio(request: Request) -> list[dict]:
        """Get Job list with extra portfolio data"""
        auth_subject = check_auth(request, scope=AuthScope.READ_JOB)
        jobs: list[JobDto] = list_job_registry(config, auth_subject)
        job_dicts: list[dict] = enrich_jobs_purge_info(jobs)
        for job_dict in job_dicts:
            job_dict['update_time_days_ago'] = days_ago(job_dict['update_time'])
            job_dict['last_call_time_days_ago'] = days_ago(job_dict['last_call_time'])
        return job_dicts

    @api.get('/job/{job_name}/{job_version}', response_model=JobDto)
    def _get_job(job_name: str, job_version: str, request: Request) -> JobDto:
        """Get details of particular Job"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.READ_JOB)
        return read_versioned_job(job_name, job_version, config)

    @api.delete('/job/{job_name}/{job_version}')
    def _delete_job(job_name: str, job_version: str, request: Request):
        """Delete Job; expects specific version (can't be latest)"""
        ensure_no_maintenance()
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.DELETE_JOB)
        username = get_username_from_token(request)
        return delete_job(job_name, job_version, config, username, plugin_engine)

    @api.post('/job/{job_name}/{job_version}/redeploy')
    def _redeploy_job(job_name: str, job_version: str, request: Request):
        """Deploy specific Job image once again (build and provision)"""
        ensure_no_maintenance()
        auth_subject = check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.DEPLOY_JOB)
        username = get_username_from_token(request)
        return redeploy_job(job_name, job_version, config, plugin_engine, username, auth_subject)

    @api.post('/job/{job_name}/{job_version}/reprovision')
    def _reprovision_job(job_name: str, job_version: str, request: Request):
        """Provision specific Job image once again to a cluster"""
        ensure_no_maintenance()
        auth_subject = check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.DEPLOY_JOB)
        username = get_username_from_token(request)
        return reprovision_job(job_name, job_version, config, plugin_engine, username, auth_subject)

    @api.post('/job/{job_name}/{job_version}/move')
    def _move_job(job_name: str, job_version: str, payload: MoveJobPayload, request: Request):
        """Move Job from one infrastructure target to another"""
        ensure_no_maintenance()
        auth_subject = check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.DEPLOY_JOB)
        username = get_username_from_token(request)
        return move_job(job_name, job_version, payload.infrastructure_target, config, plugin_engine, username, auth_subject)

    @api.get('/job/{job_name}/{job_version}/logs')
    def _get_job_logs(request: Request, job_name: str, job_version: str, tail: int = 20):
        """Get last logs of particular Job"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.READ_JOB)
        return {'logs': read_runtime_logs(job_name, job_version, tail, config)}

    @api.get('/job/{job_name}/{job_version}/logs/plain')
    def _get_plain_job_logs(request: Request, job_name: str, job_version: str, tail: int = 20):
        """Get last logs of particular Job in a plain text response"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.READ_JOB)
        content = read_runtime_logs(job_name, job_version, tail, config)
        content = strip_ansi_colors(content)
        return Response(content, media_type='text/plain; charset=utf-8')

    @api.get('/job/{job_name}/{job_version}/build-logs')
    def _get_job_build_logs(request: Request, job_name: str, job_version: str, tail: int = 0):
        """Get build logs of Job deployment attempt"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.READ_JOB)
        return {'logs': read_build_logs(job_name, job_version, tail)}

    @api.get('/job/{job_name}/{job_version}/build-logs/plain')
    def _get_plain_job_build_logs(request: Request, job_name: str, job_version: str, tail: int = 0):
        """Get build logs of Job deployment attempt in a plain text response"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.READ_JOB)
        content = read_build_logs(job_name, job_version, tail)
        content = strip_ansi_colors(content)
        return Response(content, media_type='text/plain; charset=utf-8')

    @api.get("/job/{job_name}/{job_version}/public-endpoints")
    def _get_job_public_endpoints(request: Request, job_name: str, job_version: str):
        """Get list of active public endpoints that can be accessed without authentication for a particular Job"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.READ_JOB)
        return read_active_job_public_endpoints(job_name, job_version)

    @api.put("/job/{job_name}/{job_version}/manifest")
    def _update_job_manifest(request: Request, job_name: str, job_version: str, payload: UpdateManifestPayload):
        """Update job manifest"""
        ensure_no_maintenance()
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.DEPLOY_JOB)
        return update_job_manifest(job_name, job_version, payload.manifest_yaml)

    # Async Job Calls
    @api.post('/job/async/call')
    def _create_async_job_call(payload: AsyncJobCallDto, request: Request):
        """Create new async job call record"""
        ensure_no_maintenance()
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        save_async_job_call(payload)

    @api.get('/job/async/call/{call_id}')
    def _get_async_job_call(call_id: str, request: Request) -> AsyncJobCallDto:
        """Get async job call record by ID"""
        ensure_no_maintenance()
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        model = get_async_job_call(call_id)
        return async_job_call_to_dto(model)

    @api.put('/job/async/call')
    def _update_async_job_call(payload: AsyncJobCallDto, request: Request):
        """Update async job call record"""
        ensure_no_maintenance()
        check_auth(request, scope=AuthScope.CALL_ADMIN_API)
        save_async_job_call(payload)
