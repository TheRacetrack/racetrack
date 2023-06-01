from multiprocessing import Process

import backoff
import pytest

from lifecycle.config import Config
from lifecycle.server.api import run_api_server
from lifecycle.server.metrics import unregister_metrics
from racetrack_client.utils.request import Requests, RequestError
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.socket import free_tcp_port


@pytest.mark.django_db(transaction=True)
def test_bootstrap_server():
    port = free_tcp_port()
    unregister_metrics()
    config = Config(http_port=port)
    plugin_engine = PluginEngine()
    server_process = Process(target=run_api_server, args=(config, plugin_engine))
    try:
        server_process.start()
        _check_root_endpoint_pass(port)
    finally:
        server_process.terminate()
        server_process.join()


@backoff.on_exception(backoff.fibo, RequestError, max_time=5, jitter=None)
def _check_root_endpoint_pass(port: int):
    response = Requests.get(f'http://127.0.0.1:{port}')
    response.raise_for_status()
    assert response.status_code == 200
