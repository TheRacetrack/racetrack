import backoff
import httpx
import pytest

from lifecycle.config import Config
from lifecycle.event_stream.client import EventStreamClient
from lifecycle.event_stream.server import EventStreamServer
from lifecycle.job.models_registry import create_job_model
from lifecycle.server.api import create_fastapi_app
from lifecycle.server.metrics_collector import unregister_metrics
from racetrack_client.log.logs import configure_logs
from racetrack_client.manifest import Manifest
from racetrack_client.manifest.manifest import GitManifest
from racetrack_client.utils.time import datetime_to_timestamp, now
from racetrack_commons.api.asgi.asgi_server import serve_asgi_in_background
from racetrack_commons.entities.dto import JobDto, JobStatus
from racetrack_commons.plugin.engine import PluginEngine
from racetrack_commons.socket import free_tcp_port

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.django_db(transaction=True)
def test_websocket_stream():
    configure_logs()
    unregister_metrics()
    port = free_tcp_port()
    config = Config(job_watcher_interval=0.5)
    streamer = EventStreamServer(config)
    app = create_fastapi_app(config, PluginEngine(), 'lifecycle', streamer)

    with serve_asgi_in_background(app, port):
        _wait_until_server_ready(port)

        received_events = []
        socket_client = EventStreamClient(f'ws://127.0.0.1:{port}/lifecycle/websocket/events',
                                          on_event=lambda event: received_events.append(event))

        with socket_client.connect_async():
            _wait_until(lambda: len(streamer.clients) > 0, 'no client sessions connected')
            _wait_until(lambda: streamer.watcher_thread.is_alive(), 'watcher thread not running')
            streamer.notify_clients({'event': 'dummy'})
            _wait_until_equal(received_events, [{'event': 'dummy'}], 'failed to receive dummy event')
            received_events.clear()

            new_job = JobDto(
                name='tester',
                version='0.0.0-alpha',
                status=JobStatus.RUNNING.value,
                create_time=datetime_to_timestamp(now()),
                update_time=datetime_to_timestamp(now()),
                manifest=Manifest(
                    name='tester',
                    owner_email='test@example.com',
                    git=GitManifest(
                        remote='github.com',
                    ),
                ),
                internal_name='tester-0.0.0-alpha',
                infrastructure_target='docker',
            )
            create_job_model(new_job)

            _wait_until_equal(received_events, [{'event': 'job_models_changed'}], 'failed to receive job_models_changed event')

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
