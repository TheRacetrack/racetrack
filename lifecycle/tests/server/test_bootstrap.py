import backoff

from lifecycle.config import Config
from lifecycle.server.api import create_fastapi_app
from lifecycle.server.metrics_collector import unregister_metrics
from racetrack_client.utils.request import Requests, RequestError
from racetrack_commons.api.asgi.asgi_server import serve_asgi_in_background
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.socket import free_tcp_port


def test_bootstrap_server():
    port = free_tcp_port()
    unregister_metrics()
    config = Config(http_port=port)
    plugin_engine = PluginEngine()
    app = create_fastapi_app(config, plugin_engine, 'lifecycle')
    with serve_asgi_in_background(app, port):
        _check_root_endpoint_pass(port)


@backoff.on_exception(backoff.fibo, RequestError, max_time=5, jitter=None)
def _check_root_endpoint_pass(port: int):
    response = Requests.get(f'http://127.0.0.1:{port}')
    response.raise_for_status()
    assert response.status_code == 200
