from typing import Optional, Callable
import os
from pathlib import Path

import fastapi
from fastapi import APIRouter, FastAPI
from a2wsgi import WSGIMiddleware
from werkzeug.middleware.shared_data import SharedDataMiddleware

from fatman_wrapper.entrypoint import FatmanEntrypoint
from racetrack_commons.api.asgi.proxy import TrailingSlashForwarder


def setup_webview_endpoints(
    entrypoint: FatmanEntrypoint,
    base_url: str,
    fastapi_app: FastAPI,
    api: APIRouter,
):
    webview_base_url = base_url + '/api/v1/webview'

    webview_wsgi_app = instantiate_webview_app(entrypoint, webview_base_url)
    if webview_wsgi_app is None:
        return

    wsgi_app = PathPrefixerMiddleware(webview_wsgi_app, webview_base_url)
    fastapi_app.mount('/api/v1/webview', WSGIMiddleware(wsgi_app))
    TrailingSlashForwarder.mount_path('/api/v1/webview')

    @api.get('/webview/{path:path}')
    def _fatman_webview_endpoint(path: Optional[str] = fastapi.Path(None)):
        """Call custom Webview UI pages"""
        pass  # just register endpoint in swagger, it's handled by ASGI


def instantiate_webview_app(entrypoint: FatmanEntrypoint, base_url: str) -> Optional[Callable]:
    if not hasattr(entrypoint, 'webview_app'):
        return None
    webview_app_function = getattr(entrypoint, 'webview_app')
    wsgi_app = webview_app_function(base_url)
    if wsgi_app is None:
        return None

    # serve static resources
    static_path = Path(os.getcwd()) / 'static'
    if static_path.is_dir():
        wsgi_app = SharedDataMiddleware(wsgi_app, {
            base_url + '/static': str(static_path)
        })

    return wsgi_app


class PathPrefixerMiddleware:
    def __init__(self, app, base_path: str):
        self.app = app
        self.base_path = base_path

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if not path.startswith(self.base_path):
            path = self.base_path + path

            environ['PATH_INFO'] = path
            environ['REQUEST_URI'] = path
            environ['RAW_URI'] = path

        return self.app(environ, start_response)
