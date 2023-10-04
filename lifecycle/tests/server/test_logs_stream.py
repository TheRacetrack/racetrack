from threading import Thread
from typing import Dict, Callable

from lifecycle.infrastructure.model import InfrastructureTarget
from lifecycle.monitor.base import LogsStreamer
from lifecycle.server.cache import LifecycleCache
from lifecycle.server.socketio import SocketIOServer, JobRetriever
from racetrack_client.client.socketio import LogsConsumer
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import JobDto
from racetrack_commons.socket import free_tcp_port

from tests.utils import wait_until_equal

logger = get_logger(__name__)


def test_streaming_logs():
    LifecycleCache.infrastructure_targets = {
        'dummy-infra': InfrastructureTarget(
            logs_streamer=DummyLogsStreamer(),
        ),
    }

    server = SocketIOServer(DummyJobRetriever())
    port = free_tcp_port()
    with server.run_async(port):
        fetched_logs = []
        consumer = LogsConsumer(f'http://localhost:{port}',
                                socketio_path='lifecycle/socket.io',
                                resource_properties={'job_name': 'adder', 'job_version': 'latest'},
                                on_next_line=lambda line: fetched_logs.append(line))
        with consumer.connect_async():
            wait_until_equal(fetched_logs, ['hello adder', 'more logs'], 'fetching logs failed')


class DummyLogsStreamer(LogsStreamer):
    def create_session(self, session_id: str, resource_properties: Dict[str, str], on_next_line: Callable[[str, str], None]):
        job_name = resource_properties.get('job_name')
        on_next_line(session_id, f'hello {job_name}')

        def in_background():
            on_next_line(session_id, f'more logs')

        Thread(target=in_background, daemon=True).start()


class DummyJobRetriever(JobRetriever):
    def get_job(self, job_name: str, job_version: str) -> JobDto:
        return JobDto(name=job_name, version=job_version, status='ok', create_time=0, update_time=0, infrastructure_target='dummy-infra')
