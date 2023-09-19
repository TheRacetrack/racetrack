import backoff
import httpx

from lifecycle.event_stream.client import EventStreamClient
from racetrack_client.log.logs import configure_logs


def test_socketio_stream():
    configure_logs(log_level='debug')
    received_events = []

    clients: list[EventStreamClient] = []
    clients_num = 300
    for _ in range(clients_num):
        socket_client = EventStreamClient(f'http://127.0.0.1:7102',
                                          on_event=lambda event: received_events.append(event))
        socket_client.sio.connect(socket_client.url, socketio_path=socket_client.socketio_path)
        clients.append(socket_client)

    for i in range(clients_num):
        socket_client = clients[i]
        socket_client.sio.disconnect()


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
