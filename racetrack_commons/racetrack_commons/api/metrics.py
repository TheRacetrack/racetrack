from a2wsgi import WSGIMiddleware
from fastapi import FastAPI
from prometheus_client import Counter, Histogram
from prometheus_client.exposition import make_wsgi_app
from prometheus_client.registry import REGISTRY

from racetrack_commons.api.asgi.proxy import TrailingSlashForwarder

metric_internal_server_errors = Counter(
    'commons_internal_server_errors',
    'Number of Internal Server Errors (500) caught by error handler',
)
metric_request_duration = Histogram(
    'commons_request_duration',
    'Duration of API requests in seconds',
    buckets=(.001, .0025, .005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5,
             10.0, 25.0, 50.0, 75.0, 100.0, 250.0, 500.0, 750.0, 1000.0, float("inf")),
)
metric_requests_started = Counter(
    'commons_requests_started',
    'Total number of started API requests (may be not finished yet)',
)
metric_requests_done = Counter(
    'commons_requests_done',
    'Total number of finished API requests (processed and done)',
)


def setup_metrics_endpoint(api: FastAPI):

    metrics_app = make_wsgi_app(REGISTRY)
    api.mount('/metrics', WSGIMiddleware(metrics_app))
    TrailingSlashForwarder.mount_path('/metrics')

    @api.get('/metrics', tags=['root'])
    def _metrics_endpoint():
        """List current Prometheus metrics"""
        pass  # just register endpoint in swagger, it's handled by ASGI
