from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from image_builder.config import Config
from image_builder.build import build_job_image
from image_builder.health import health_response
from image_builder.scheduler import schedule_tasks_async
from racetrack_client.client_config.io import load_credentials_from_dict
from racetrack_client.log.logs import configure_logs
from racetrack_client.manifest.load import load_manifest_from_dict
from racetrack_client.utils.config import load_config
from racetrack_commons.api.asgi.asgi_server import serve_asgi_app
from racetrack_commons.api.asgi.fastapi import create_fastapi
from racetrack_commons.api.metrics import setup_metrics_endpoint
from racetrack_commons.plugin.engine import PluginEngine


def run_api_server():
    """Serve API for building images from workspaces on demand"""
    configure_logs()
    config: Config = load_config(Config)

    schedule_tasks_async(config)

    plugin_engine = PluginEngine(config.plugins_dir)
    fastapi_app = configure_api(config, plugin_engine)

    serve_asgi_app(
        fastapi_app, http_addr=config.http_addr, http_port=config.http_port,
    )


def configure_api(config: Config, plugin_engine: PluginEngine) -> FastAPI:
    """Create FastAPI app and register all endpoints without running a server"""
    fastapi_app = create_fastapi(
        title='Image Builder',
        description='Builder of Job images',
        request_access_log=True,
        response_access_log=True,
    )

    _setup_health_endpoint(fastapi_app)
    setup_metrics_endpoint(fastapi_app)

    api_router = APIRouter(tags=['API'])
    _setup_api_endpoints(api_router, config, plugin_engine)
    fastapi_app.include_router(api_router, prefix="/api/v1")

    return fastapi_app


def _setup_health_endpoint(api: FastAPI):
    @api.get("/health", tags=['root'])
    def _health():
        """Report current application status"""
        content, status = health_response()
        return JSONResponse(content=content, status_code=status)


def _setup_api_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):

    class CredentialsModel(BaseModel):
        username: str = Field(examples=["admin"])
        password: str = Field(examples=["hunter2"])

    class BuildPayloadModel(BaseModel):
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
        secret_build_env: Optional[Dict[str, Any]] = Field(
            default=None,
            description='secret environment vars applied on build',
            examples=[{
                'GIT_PASSWD': '5ecr3t',
            }],
        )
        tag: str = Field(description='image tag', examples=['2021-08-12T094058'])
        build_context: Optional[str] = Field(
            default=None,
            description='encoded build context',
            examples=[''],
        )
        deployment_id: str = Field(
            description='unique ID of a deployment',
            examples=['681d0416-c95d-4cb8-bbd0-bb81d3a46044'],
        )

    class BuildingResultModel(BaseModel):
        image_names: List[str] = Field(
            description='List of full names of built images',
            examples=[['ghcr.io/racetrack/job-entrypoint/adder:latest']],
        )
        logs: str = Field(
            description='build logs output',
            examples=['#1 DONE 1.0s'],
        )
        error: Optional[str] = Field(
            default=None,
            description='error message',
            examples=['docker command not found'],
        )

    @api.post('/build', response_model=BuildingResultModel)
    def _build(payload: BuildPayloadModel):
        """Build Job image from a manifest"""
        manifest = load_manifest_from_dict(payload.manifest)
        git_credentials = load_credentials_from_dict(payload.git_credentials)
        tag = payload.tag
        secret_build_env = payload.secret_build_env or {}
        build_context = payload.build_context
        deployment_id = payload.deployment_id
        image_names, logs, error = build_job_image(
            config, manifest, git_credentials, secret_build_env, tag,
            build_context, deployment_id, plugin_engine,
        )
        return {
            'image_names': image_names,
            'logs': logs,
            'error': error,
        }
