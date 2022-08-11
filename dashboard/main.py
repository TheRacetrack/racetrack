#!/usr/bin/env
import os

from racetrack_client.log.logs import configure_logs
from racetrack_commons.api.asgi.asgi_server import serve_asgi_app
from racetrack_commons.api.debug import is_deployment_local

from app.asgi import application


def run_asgi_app():
    configure_logs()

    http_addr = '0.0.0.0'
    http_port = int(os.environ.get('DASHBOARD_PORT', 7203))

    if is_deployment_local():
        app = 'app.asgi:application'
    else:
        app = application

    serve_asgi_app(app, http_addr, http_port, access_log=True)


if __name__ == '__main__':
    run_asgi_app()
