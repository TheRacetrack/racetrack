from fastapi import FastAPI
from prometheus_client.exposition import make_asgi_app
from prometheus_client.registry import REGISTRY
from racetrack_commons.api.asgi.proxy import TrailingSlashForwarder


def setup_metrics_endpoint(api: FastAPI):

    metrics_app = make_asgi_app(REGISTRY)
    api.mount('/metrics', metrics_app)
    TrailingSlashForwarder.mount_path('/metrics')

    @api.get('/metrics', tags=['root'])
    def _metrics_endpoint():
        """List current Prometheus metrics"""
        pass  # just register endpoint in swagger, it's handled by ASGI
