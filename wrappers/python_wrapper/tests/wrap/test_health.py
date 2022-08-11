import os
import socket
from multiprocessing import Process

import backoff
from fastapi.testclient import TestClient

from fatman_wrapper.config import Config
from fatman_wrapper.health import HealthState
from fatman_wrapper.loader import instantiate_class_entrypoint
from fatman_wrapper.main import run_configured_entrypoint
from fatman_wrapper.wrapper import create_api_app
from racetrack_client.utils.request import Requests, RequestError


def test_health_endpoints():
    os.environ['FATMAN_NAME'] = 'skynet'
    os.environ['FATMAN_VERSION'] = '1.2.3'
    os.environ['GIT_VERSION'] = '1.2.3-2-g123456'
    os.environ['DEPLOYED_BY_RACETRACK_VERSION'] = '0.0.15'
    model = instantiate_class_entrypoint('sample/adder_model.py', None)
    health_state = HealthState(live=True, ready=True)
    api_app = create_api_app(model, health_state)

    client = TestClient(api_app)

    response = client.get('/health')
    assert response.status_code == 200
    obj = response.json()
    assert obj['status'] == 'pass'
    assert obj['fatman_name'] == 'skynet'
    assert obj['fatman_version'] == '1.2.3'
    assert obj['git_version'] == '1.2.3-2-g123456'
    assert obj['deployed_by_racetrack_version'] == '0.0.15'

    response = client.get('/live')
    assert response.status_code == 200

    response = client.get('/ready')
    assert response.status_code == 200


def test_live_but_not_ready():
    model = instantiate_class_entrypoint('sample/adder_model.py', None)
    health_state = HealthState(live=True, ready=False)
    api_app = create_api_app(model, health_state)

    client = TestClient(api_app)

    response = client.get('/health')
    assert response.status_code == 500

    response = client.get('/live')
    assert response.status_code == 200

    response = client.get('/ready')
    assert response.status_code == 500


def test_ready_but_not_live():
    model = instantiate_class_entrypoint('sample/adder_model.py', None)
    health_state = HealthState(live=False, ready=True)
    api_app = create_api_app(model, health_state)

    client = TestClient(api_app)

    response = client.get('/health')
    assert response.status_code == 500

    response = client.get('/live')
    assert response.status_code == 500

    response = client.get('/ready')
    assert response.status_code == 200


def test_bootstrap_server():
    port = free_tcp_port()
    config = Config(http_port=port)

    def target():
        run_configured_entrypoint(config, 'sample/adder_model.py')

    server_process = Process(target=target)
    try:
        server_process.start()

        check_health_pass(port)

        response = Requests.get(f'http://127.0.0.1:{port}/live')
        response.raise_for_status()
        assert response.status_code == 200

        response = Requests.get(f'http://127.0.0.1:{port}/ready')
        response.raise_for_status()
        assert response.status_code == 200
    finally:
        server_process.terminate()
        server_process.join()


def test_survive_syntax_error():
    port = free_tcp_port()
    config = Config(http_port=port)

    def target():
        run_configured_entrypoint(config, 'sample/faulty_syntax.py')

    server_process = Process(target=target)
    try:
        server_process.start()

        error = check_live_fails(port)
        assert error, 'returned error is empty'
        assert 'cause=SyntaxError' in error, 'returned error is not SyntaxError'

        response = Requests.get(f'http://127.0.0.1:{port}/ready')
        assert response.status_code == 500
    finally:
        server_process.terminate()
        server_process.join()


def test_survive_module_error():
    port = free_tcp_port()
    config = Config(http_port=port)

    def target():
        run_configured_entrypoint(config, 'sample/faulty_import.py')

    server_process = Process(target=target)
    try:
        server_process.start()

        error = check_live_fails(port)
        assert error, 'returned error is empty'
        assert 'cause=ModuleNotFoundError' in error, 'returned error is not ModuleNotFoundError'
        assert 'faulty_import.py:3' in error, 'traceback not included in error'
    finally:
        server_process.terminate()
        server_process.join()


@backoff.on_exception(backoff.fibo, RequestError, max_time=5, jitter=None)
def check_health_pass(port: int):
    response = Requests.get(f'http://127.0.0.1:{port}/health')
    response.raise_for_status()
    assert response.status_code == 200
    assert response.json().get('status') == 'pass'


@backoff.on_exception(backoff.fibo, (RequestError, AssertionError), max_time=5, jitter=None)
def check_live_fails(port: int) -> str:
    response = Requests.get(f'http://127.0.0.1:{port}/live')
    assert response.status_code == 500
    return response.json().get('error')


def free_tcp_port() -> int:
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port
