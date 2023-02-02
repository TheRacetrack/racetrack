from typing import Dict

import backoff

from lifecycle.monitor.base import LogsStreamer
from lifecycle.server.socketio import SocketIOServer
from racetrack_client.client.socketio import LogsConsumer
from racetrack_client.log.logs import get_logger
from tests.server.socket import free_tcp_port

logger = get_logger(__name__)


def test_streaming_logs():
    logs_streamer = SayHelloLogsStreamer()
    server = SocketIOServer([logs_streamer])
    port = free_tcp_port()
    with server.run_async(port):
        fetched_logs = []
        consumer = LogsConsumer(f'http://localhost:{port}',
                                socketio_path='lifecycle/socket.io',
                                resource_properties={'job_name': 'adder'},
                                on_next_line=lambda line: fetched_logs.append(line))
        with consumer.connect_async():
            _wait_until_equal(fetched_logs, ['hello adder'], 'fetching past logs failed')

            logs_streamer.broadcast(logs_streamer.last_session_id, message='more logs')
            _wait_until_equal(fetched_logs, ['hello adder', 'more logs'], 'fetching next logs failed')


class SayHelloLogsStreamer(LogsStreamer):
    def create_session(self, session_id: str, resource_properties: Dict[str, str]):
        self.last_session_id = session_id
        job_name = resource_properties.get('job_name')
        self.broadcast(session_id, f'hello {job_name}')


@backoff.on_exception(backoff.expo, AssertionError, factor=0.1, max_time=10, jitter=None)
def _wait_until_equal(collection1, collection2, err_message: str):
    assert collection1 == collection2, err_message
