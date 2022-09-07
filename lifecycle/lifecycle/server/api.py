import os

import django
from fastapi import APIRouter
from a2wsgi import WSGIMiddleware
from starlette.types import ASGIApp

from lifecycle.config import Config
from lifecycle.django.app.asgi import application as django_app
from lifecycle.endpoints.audit import setup_audit_endpoints
from lifecycle.endpoints.auth import setup_auth_endpoints
from lifecycle.endpoints.info import setup_info_endpoints
from lifecycle.monitor.monitors import get_logs_streamer
from lifecycle.endpoints.health import setup_health_endpoint
from lifecycle.endpoints.deploy import setup_deploy_endpoints
from lifecycle.endpoints.esc import setup_esc_endpoints
from lifecycle.endpoints.fatman import setup_fatman_endpoints
from lifecycle.endpoints.user import setup_user_endpoints
from lifecycle.server.socketio import SocketIOServer
from racetrack_client.log.logs import get_logger
from racetrack_commons.api.asgi.asgi_server import serve_asgi_app
from racetrack_commons.api.asgi.dispatcher import AsgiDispatcher
from racetrack_commons.api.asgi.error_handler import register_error_handlers
from racetrack_commons.api.asgi.fastapi import create_fastapi
from racetrack_commons.api.asgi.proxy import mount_at_base_path
from racetrack_commons.api.metrics import setup_metrics_endpoint
from racetrack_commons.auth.methods import get_racetrack_authorizations_methods
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.telemetry.otlp import setup_opentelemetry

logger = get_logger(__name__)
BASE_URL = '/lifecycle'


def run_api_server(config: Config, plugin_engine: PluginEngine):
    """Create app from config and run ASGI HTTP server"""
    app = create_fastapi_app(config, plugin_engine)
    serve_asgi_app(app, config.http_addr, config.http_port)


def create_fastapi_app(config: Config, plugin_engine: PluginEngine) -> ASGIApp:
    """Create FastAPI app and register all endpoints without running a server"""
    fastapi_app = create_fastapi(
        title='Lifecycle API Server',
        description='Management of deployed Fatman Workloads',
        base_url=BASE_URL,
        authorizations=get_racetrack_authorizations_methods(),
        request_access_log=True,
        response_access_log=True,
        handle_errors=False,
    )

    setup_health_endpoint(fastapi_app, config)
    setup_metrics_endpoint(fastapi_app)

    api_router = APIRouter(tags=['API'])
    setup_api_endpoints(api_router, config, plugin_engine)
    fastapi_app.include_router(api_router, prefix="/api/v1")

    sio_wsgi_app = setup_socket_io_server(config, plugin_engine)

    if config.open_telemetry_enabled:
        setup_opentelemetry(fastapi_app, config.open_telemetry_endpoint, 'lifecycle', {})

    register_error_handlers(fastapi_app)

    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    django.setup()

    proxy = mount_at_base_path(
        fastapi_app,
        BASE_URL,
    )

    dispatcher = AsgiDispatcher({
        '/admin': django_app,
        BASE_URL + '/admin': django_app,
        '/static': django_app,
        BASE_URL + '/static': django_app,
        '/socket.io': WSGIMiddleware(sio_wsgi_app),
        BASE_URL + '/socket.io': WSGIMiddleware(sio_wsgi_app),
    }, default=proxy)

    return dispatcher


def setup_api_endpoints(api: APIRouter, config: Config, plugin_engine: PluginEngine):
    if not config.auth_required:
        logger.warning("Authentication is not required")

    setup_deploy_endpoints(api, config, plugin_engine)
    setup_fatman_endpoints(api, config, plugin_engine)
    setup_esc_endpoints(api, config)
    setup_user_endpoints(api, config)
    setup_info_endpoints(api, config, plugin_engine)
    setup_audit_endpoints(api, config)
    setup_auth_endpoints(api, config)


def setup_socket_io_server(config: Config, plugin_engine: PluginEngine):
    """Configure Socket.IO server for streaming data to clients"""
    logs_streamer = get_logs_streamer(config, plugin_engine)
    return SocketIOServer(logs_streamer).wsgi_app
