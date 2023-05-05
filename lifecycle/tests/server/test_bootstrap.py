from multiprocessing import Process

import backoff

from lifecycle.config import Config
from lifecycle.server.api import run_api_server
from racetrack_client.utils.request import Requests, RequestError
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.socket import free_tcp_port


def test_bootstrap_server():
    port = free_tcp_port()
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
