from typing import Any, Dict, Optional
from fastapi import APIRouter, Request

from pydantic import BaseModel, ConfigDict, Field

from lifecycle.auth.check import check_auth
from lifecycle.auth.authenticate import get_username_from_token
from lifecycle.config import Config
from lifecycle.config.maintenance import ensure_no_maintenance
from lifecycle.deployer.builder import build_job_in_background
from lifecycle.deployer.deploy import deploy_job_in_background
from lifecycle.job.deployment import check_deployment_result, save_deployment_phase, list_recent_deployments, save_deployment_warnings
from lifecycle.server.metrics import metric_requested_job_deployments
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_client.client.env import load_secret_vars_from_dict
from racetrack_client.client_config.io import load_credentials_from_dict
from racetrack_client.manifest.load import load_manifest_from_dict


def setup_deploy_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):
    class CredentialsModel(BaseModel):
        username: str = Field(examples=["admin"])
        password: str = Field(examples=["hunter2"])

    class DeployPayloadModel(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)

        manifest: Dict[str, Any] = Field(
            description='Manifest - build recipe for a Job',
            examples=[{
                'name': 'adder',
                'jobtype': 'python3',
                'owner_email': 'nobody@example.com',
                'git': {
                    'remote': '.',
                    'directory': 'sample/python-class',
                },
                'jobtype_extra': {
                    'requirements_path': 'requirements.txt',
                    'entrypoint_path': 'adder.py',
                },
            }],
        )
        git_credentials: Optional[CredentialsModel] = Field(
            default=None,
            description='git repository credentials',
        )
        secret_vars: Optional[Dict[str, Any]] = Field(
            default=None,
            description='secret environment vars',
            examples=[{
                'build_env': {
                    'GIT_PASS': '5ecr3t',
                },
                'runtime_env': {
                    'PGPASSWORD': '5ecr3t',
                },
            }],
        )
        build_context: Optional[str] = Field(
            default=None,
            description='encoded build context',
            examples=[''],
        )
        force: Optional[bool] = Field(
            default=None,
            description='overwrite existing job',
            examples=[False],
        )
        build_flags: Optional[list[str]] = Field(
            default=[],
            description='list of build flags',
            examples=['--no-cache'],
        )

    @api.post('/deploy')
    def _deploy(payload: DeployPayloadModel, request: Request):
        """Start deployment of Job"""
        ensure_no_maintenance()
        auth_subject = check_auth(request)
        assert auth_subject is not None
        metric_requested_job_deployments.inc()

        manifest = load_manifest_from_dict(payload.manifest)
        git_credentials = load_credentials_from_dict(payload.git_credentials.model_dump() if payload.git_credentials else None)
        secret_vars = load_secret_vars_from_dict(payload.secret_vars)
        build_context = payload.build_context
        force = payload.force if payload.force is not None else False
        build_flags = payload.build_flags if payload.build_flags else []
        username = get_username_from_token(request)
        deployment_id = deploy_job_in_background(
            config, manifest, git_credentials, secret_vars, build_context,
            force, plugin_engine, username, auth_subject, build_flags
        )
        return {"id": deployment_id}

    @api.get('/deploy')
    def _get_deployments(request: Request, limit: int = 100):
        """List recent deployment attempts"""
        check_auth(request)
        return list_recent_deployments(limit)

    @api.post('/build')
    def _build(payload: DeployPayloadModel, request: Request):
        """Build Job image"""
        check_auth(request)
        manifest = load_manifest_from_dict(payload.manifest)
        git_credentials = load_credentials_from_dict(payload.git_credentials.model_dump() if payload.git_credentials else None)
        secret_vars = load_secret_vars_from_dict(payload.secret_vars)
        build_context = payload.build_context
        username = get_username_from_token(request)
        deployment_id = build_job_in_background(config, manifest, git_credentials, secret_vars,
                                                build_context, username, plugin_engine)
        return {"id": deployment_id}

    @api.get('/deploy/{deploy_id}')
    def _get_deployment(deploy_id: str, request: Request):
        """Check deployment status/result by its ID"""
        check_auth(request)
        return check_deployment_result(deploy_id, config)

    class DeploymentPhase(BaseModel):
        phase: str = Field(description='phase of the deployment')

    @api.put('/deploy/{deploy_id}/phase')
    def _update_deployment_phase(deploy_id: str, payload: DeploymentPhase, request: Request):
        """Update deployment's phase"""
        check_auth(request)
        save_deployment_phase(deploy_id, payload.phase)

    class DeploymentWarnings(BaseModel):
        warnings: str = Field(description='deployment warnings')

    @api.put('/deploy/{deploy_id}/warnings')
    def _update_deployment_warnings(deploy_id: str, payload: DeploymentWarnings, request: Request):
        """Update deployment's warnings"""
        check_auth(request)
        save_deployment_warnings(deploy_id, payload.warnings)
