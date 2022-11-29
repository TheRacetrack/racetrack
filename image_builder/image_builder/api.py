from typing import Any, Dict, Optional

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from image_builder.config import Config
from image_builder.build import build_fatman_image
from image_builder.health import health_response
from image_builder.job_type import list_available_job_types
from image_builder.scheduler import schedule_tasks_async
from racetrack_client.client_config.io import load_credentials_from_dict
from racetrack_client.log.logs import init_logs, configure_logs
from racetrack_client.manifest.load import load_manifest_from_dict
from racetrack_client.utils.config import load_config
from racetrack_commons.api.asgi.asgi_server import serve_asgi_app
from racetrack_commons.api.asgi.fastapi import create_fastapi
from racetrack_commons.api.metrics import setup_metrics_endpoint
from racetrack_commons.plugin.engine import PluginEngine


def run_api_server():
    """Serve API for building images from workspaces on demand"""
    init_logs()
    config: Config = load_config(Config)
    configure_logs(log_level=config.log_level)

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
        description='Builder of Fatman images',
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
        username: str = Field(example="admin")
        password: str = Field(example="hunter2")

    class BuildPayloadModel(BaseModel):
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
        secret_build_env: Optional[Dict[str, Any]] = Field(
            default=None,
            description='secret environment vars applied on build',
            example={
                'GIT_PASSWD': '5ecr3t',
            },
        )
        tag: str = Field(description='image tag', example='2021-08-12T094058')
        build_context: Optional[str] = Field(
            default=None,
            description='encoded build context',
            example='',
        )
        deployment_id: str = Field(
            description='unique ID of a deployment',
            example='681d0416-c95d-4cb8-bbd0-bb81d3a46044',
        )

    class BuildingResultModel(BaseModel):
        image_name: str = Field(
            description='full docker image name with docker tag',
            example='ghcr.io/racetrack/fatman-entrypoint/adder:latest',
        )
        logs: str = Field(
            description='build logs output',
            example='#1 DONE 1.0s',
        )
        error: Optional[str] = Field(
            default=None,
            description='error message',
            example='docker command not found',
        )

    @api.post('/build', response_model=BuildingResultModel)
    def _build(payload: BuildPayloadModel):
        """Build Fatman image from a manifest"""
        manifest = load_manifest_from_dict(payload.manifest)
        git_credentials = load_credentials_from_dict(payload.git_credentials)
        tag = payload.tag
        secret_build_env = payload.secret_build_env or {}
        build_context = payload.build_context
        deployment_id = payload.deployment_id
        image_name, logs, error = build_fatman_image(
            config, manifest, git_credentials, secret_build_env, tag,
            build_context, deployment_id, plugin_engine,
        )
        return {
            'image_name': image_name,
            'logs': logs,
            'error': error,
        }

    @api.get('/job_type/versions')
    def _get_job_type_versions():
        """List available job type versions"""
        return list_available_job_types(plugin_engine)
