import backoff
import httpx
import pytest

from lifecycle.config import Config
from lifecycle.event_stream.client import EventStreamClient
from lifecycle.event_stream.server import EventStreamServer
from lifecycle.server.api import create_fastapi_app
from lifecycle.server.metrics import unregister_metrics
from racetrack_client.log.logs import configure_logs
from racetrack_commons.api.asgi.asgi_server import serve_asgi_in_background
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.socket import free_tcp_port

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return 'asyncio'


def test_socketio_stream():
    configure_logs(log_level='debug')
    unregister_metrics()
    port = free_tcp_port()
    streamer = EventStreamServer()
    app = create_fastapi_app(Config(), PluginEngine(), 'lifecycle', streamer)

    with serve_asgi_in_background(app, port):
        _wait_until_server_ready(port)

        received_events = []
        socket_client = EventStreamClient(f'http://127.0.0.1:{port}',
                                          on_event=lambda event: received_events.append(event))

        with socket_client.connect_async():
            _wait_until(lambda: len(streamer.clients) > 0, 'no client sessions connected')
            _wait_until(lambda: streamer.watcher_thread.is_alive(), 'watcher thread not running')
            streamer.notify_clients({'event': 'happened'})
            _wait_until_equal(received_events, [{'event': 'happened'}], 'fetching next event failed')

        _wait_until(lambda: len(streamer.clients) == 0, 'all clients should be disconnected')
        _wait_until(lambda: not streamer.watcher_thread.is_alive(), 'watcher thread should be dead')


@backoff.on_exception(backoff.fibo, httpx.RequestError, max_time=5, jitter=None)
def _wait_until_server_ready(port: int):
    response = httpx.get(f'http://127.0.0.1:{port}/ready')
    assert response.status_code == 200


@backoff.on_exception(backoff.expo, AssertionError, factor=0.1, max_time=10, jitter=None)
def _wait_until_equal(c1, c2, err_message: str):
    assert c1 == c2, err_message


@backoff.on_exception(backoff.expo, AssertionError, factor=0.1, max_time=10, jitter=None)
def _wait_until(condition, err_message: str):
    assert condition, err_message
