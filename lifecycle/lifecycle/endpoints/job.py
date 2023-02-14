from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from lifecycle.auth.check import check_auth
from lifecycle.config import Config
from lifecycle.deployer.redeploy import redeploy_job, reprovision_job, move_job
from lifecycle.job.graph import build_job_dependencies_graph
from lifecycle.job.registry import (
    delete_job,
    list_job_families,
    list_job_registry,
    read_versioned_job,
)
from lifecycle.job.public_endpoints import read_active_job_public_endpoints
from lifecycle.job.logs import read_build_logs, read_runtime_logs
from lifecycle.auth.authenticate import get_username_from_token
from racetrack_commons.entities.dto import JobDto, JobFamilyDto
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.auth.scope import AuthScope


def setup_job_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):

    class JobResultModel(BaseModel):
        id: Optional[str] = Field(
            default=None,
            description='ID of Job',
            example='00000000-1111-2222-3333-444444444444',
        )
        name: Optional[str] = Field(
            default=None,
            description='name of Job',
            example='adder',
        )
        version: Optional[str] = Field(
            default=None,
            description='version of Job',
            example='0.0.1',
        )
        deployed_by: Optional[str] = Field(
            default=None,
            description='username of the last deployer',
            example='nobody',
        )
        manifest: Optional[Dict[str, Any]] = Field(
            default=None,
            description='Manifest - build recipe for a Job',
            example={
                'name': 'adder',
                'lang': 'python3',
                'owner_email': 'nobody@example.com',
                'git': {
                    'remote': '.',
                    'directory': 'sample/python-class',
                },
                'python': {
                    'requirements_path': 'requirements.txt',
                    'entrypoint_path': 'adder.py',
                },
            },
        )
        error: Optional[str] = Field(
            default=None,
            description='error message',
            example='you have no power here',
        )
        status: Optional[str] = Field(
            default=None,
            description='status name',
            example='all ok',
        )
        internal_name: Optional[str] = Field(
            default=None,
            description='internal name of the Job',
            example='job-adder-v-0-0-1',
        )
        create_time: Optional[int] = Field(
            default=None,
            description='timestamp of creation',
            example=1000000,
        )
        update_time: Optional[int] = Field(
            default=None,
            description='timestamp of last update',
            example=1000000,
        )

    class MoveJobPayload(BaseModel):
        infrastructure_target: str = Field(description='text content of configuration file')

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

    @api.get('/job_graph')
    def _get_job_graph(request: Request):
        """Get Job dependencies graph"""
        auth_subject = check_auth(request, scope=AuthScope.READ_JOB)
        return build_job_dependencies_graph(config, auth_subject)

    @api.get('/job/{job_name}/{job_version}', response_model=JobResultModel)
    def _get_job(job_name: str, job_version: str, request: Request):
        """Get details of particular Job"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.READ_JOB)
        return read_versioned_job(job_name, job_version, config)

    @api.delete('/job/{job_name}/{job_version}')
    def _delete_job(job_name: str, job_version: str, request: Request):
        """Delete Job; expects specific version (can't be latest)"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.DELETE_JOB)
        username = get_username_from_token(request)
        return delete_job(job_name, job_version, config, username, plugin_engine)

    @api.post('/job/{job_name}/{job_version}/redeploy')
    def _redeploy_job(job_name: str, job_version: str, request: Request):
        """Deploy specific Job image once again (build and provision)"""
        auth_subject = check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.DEPLOY_JOB)
        username = get_username_from_token(request)
        return redeploy_job(job_name, job_version, config, plugin_engine, username, auth_subject)

    @api.post('/job/{job_name}/{job_version}/reprovision')
    def _reprovision_job(job_name: str, job_version: str, request: Request):
        """Provision specific Job image once again to a cluster"""
        auth_subject = check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.DEPLOY_JOB)
        username = get_username_from_token(request)
        return reprovision_job(job_name, job_version, config, plugin_engine, username, auth_subject)

    @api.post('/job/{job_name}/{job_version}/move')
    def _move_job(job_name: str, job_version: str, payload: MoveJobPayload, request: Request):
        """Move Job from one infrastructure target to another"""
        auth_subject = check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.DEPLOY_JOB)
        username = get_username_from_token(request)
        return move_job(job_name, job_version, payload.infrastructure_target, config, plugin_engine, username, auth_subject)

    @api.get('/job/{job_name}/{job_version}/logs')
    def _get_job_logs(request: Request, job_name: str, job_version: str, tail: int = 20):
        """Get last logs of particular Job"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.READ_JOB)
        return {'logs': read_runtime_logs(job_name, job_version, tail, config, plugin_engine)}

    @api.get('/job/{job_name}/{job_version}/build-logs')
    def _get_job_build_logs(request: Request, job_name: str, job_version: str, tail: int = 0):
        """Get build logs of Job deployment attempt"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.READ_JOB)
        return {'logs': read_build_logs(job_name, job_version, tail)}

    @api.get("/job/{job_name}/{job_version}/public-endpoints")
    def _get_job_public_endpoints(request: Request, job_name: str, job_version: str):
        """Get list of active public endpoints that can be accessed without authentication for a particular Job"""
        check_auth(request, job_name=job_name, job_version=job_version, scope=AuthScope.READ_JOB)
        return read_active_job_public_endpoints(job_name, job_version)
