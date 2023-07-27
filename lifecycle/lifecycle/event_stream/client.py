import contextlib
import threading
from typing import Callable

import socketio

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class EventStreamClient:
    def __init__(
        self,
        url: str,
        on_event: Callable[[dict], None],
        socketio_path: str = 'lifecycle/socketio/events',
    ):
        self.url = url
        self.socketio_path = socketio_path
        self.sio = socketio.Client(reconnection=True, ssl_verify=False)

        @self.sio.event
        def connect():
            logger.debug('Socket.IO connection established')

        @self.sio.event
        def connect_error(data):
            logger.error(f'Socket.IO connection error: {data}')

        @self.sio.event
        def disconnect():
            logger.debug('Disconnected from Socket.IO server')

        @self.sio.event
        def broadcast_event(data):
            logger.debug(f'Event received: {data}')
            on_event(data)
            return True

    @contextlib.contextmanager
    def connect_async(self):
        self.sio.connect(self.url, socketio_path=self.socketio_path)
        try:
            threading.Thread(
                target=lambda: self.sio.wait(),
                daemon=True,
            ).start()
            yield
        finally:
            self.sio.disconnect()
