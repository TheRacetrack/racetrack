from typing import Any, Dict, Optional
from fastapi import APIRouter, Request

from lifecycle.auth.check import check_auth
from lifecycle.auth.authenticate import get_username_from_token
from lifecycle.config import Config
from lifecycle.deployer.builder import build_fatman_in_background
from lifecycle.deployer.deploy import deploy_fatman_in_background
from lifecycle.fatman.deployment import check_deployment_result
from lifecycle.server.metrics import metric_requested_fatman_deployments
from pydantic import BaseModel, Field
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_client.client.env import load_secret_vars_from_dict
from racetrack_client.client_config.io import load_credentials_from_dict
from racetrack_client.manifest.load import load_manifest_from_dict


def setup_deploy_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):

    class CredentialsModel(BaseModel):
        username: str = Field(example="admin")
        password: str = Field(example="hunter2")

    class DeployPayloadModel(BaseModel, arbitrary_types_allowed=True):
        manifest: Dict[str, Any] = Field(
            description='Manifest - build recipe for a Fatman',
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
        git_credentials: Optional[CredentialsModel] = Field(
            default=None,
            description='git repository credentials',
        )
        secret_vars: Optional[Dict[str, Any]] = Field(
            default=None,
            description='secret environment vars',
            example={
                'build_env': {
                    'GIT_PASS': '5ecr3t',
                },
                'runtime_env': {
                    'PGPASSWORD': '5ecr3t',
                },
            },
        )
        build_context: Optional[str] = Field(
            default=None,
            description='encoded build context',
            example='',
        )
        force: Optional[bool] = Field(
            default=None,
            description='overwrite existing fatman',
            example=False,
        )

    @api.post('/deploy')
    def _deploy(payload: DeployPayloadModel, request: Request):
        """Start deployment of Fatman"""
        check_auth(request)
        metric_requested_fatman_deployments.inc()

        manifest = load_manifest_from_dict(payload.manifest)
        git_credentials = load_credentials_from_dict(payload.git_credentials)
        secret_vars = load_secret_vars_from_dict(payload.secret_vars)
        build_context = payload.build_context
        force = payload.force if payload.force is not None else False
        username = get_username_from_token(request)
        auth_subject = check_auth(request)
        deployment_id = deploy_fatman_in_background(
            config, manifest, git_credentials, secret_vars, build_context,
            force, plugin_engine, username, auth_subject,
        )
        return {"id": deployment_id}

    @api.post('/build')
    def _build(payload: DeployPayloadModel, request: Request):
        """Build Fatman image"""
        check_auth(request)
        manifest = load_manifest_from_dict(payload.manifest)
        git_credentials = load_credentials_from_dict(payload.git_credentials)
        secret_vars = load_secret_vars_from_dict(payload.secret_vars)
        build_context = payload.build_context
        username = get_username_from_token(request)
        deployment_id = build_fatman_in_background(config, manifest, git_credentials, secret_vars,
                                                   build_context, username, plugin_engine)
        return {"id": deployment_id}

    @api.get('/deploy/{deploy_id}')
    def _get_deployment(deploy_id: str, request: Request):
        """Check deployment status/result by its ID"""
        check_auth(request)
        return check_deployment_result(deploy_id, config)
