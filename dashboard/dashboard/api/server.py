import os

from starlette.types import ASGIApp

from racetrack_commons.api.asgi.fastapi import create_fastapi
from racetrack_commons.auth.methods import get_racetrack_authorizations_methods
from racetrack_client.log.logs import configure_logs, get_logger
from racetrack_commons.api.asgi.asgi_server import serve_asgi_app
from racetrack_commons.api.asgi.proxy import mount_at_base_path

from dashboard.api.webview import setup_web_views
from dashboard.api.api import setup_api_endpoints
from dashboard.api.health import setup_health_endpoint

logger = get_logger(__name__)


def run_server():
    configure_logs(log_level='debug')

    http_port = int(os.environ.get('DASHBOARD_PORT', 7203))
    app = create_fastapi_app()

    serve_asgi_app(app, http_port)


def create_fastapi_app() -> ASGIApp:
    """Create FastAPI app and register all endpoints without running a server"""
    base_url = '/dashboard'
    app = create_fastapi(
        title='Dashboard API Server',
        description='',
        base_url=base_url,
        authorizations=get_racetrack_authorizations_methods(),
        request_access_log=True,
        response_access_log=True,
        handle_errors=True,
        docs_url='/docs',
    )

    setup_health_endpoint(app)
    setup_api_endpoints(app)
    setup_web_views(app)

    return mount_at_base_path(
        app,
        base_url,
    )
