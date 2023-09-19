from fastapi import FastAPI
from prometheus_client import Counter
from prometheus_client.exposition import make_asgi_app
from prometheus_client.registry import REGISTRY
from racetrack_commons.api.asgi.proxy import TrailingSlashForwarder

metric_internal_server_errors = Counter(
    'internal_server_errors',
    'Number of Internal Server Errors (500) caught by error handler',
)


def setup_metrics_endpoint(api: FastAPI):

    metrics_app = make_asgi_app(REGISTRY)
    api.mount('/metrics', metrics_app)
    TrailingSlashForwarder.mount_path('/metrics')

    @api.get('/metrics', tags=['root'])
    def _metrics_endpoint():
        """List current Prometheus metrics"""
        pass  # just register endpoint in swagger, it's handled by ASGI
