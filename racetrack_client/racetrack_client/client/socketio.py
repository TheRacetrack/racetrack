import contextlib
import threading
from typing import Callable, Dict

import socketio

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class LogsConsumer:
    def __init__(self,
                 url: str,
                 socketio_path: str,
                 resource_properties: Dict[str, str],
                 on_next_line: Callable[[str], None]):
        """
        Consumer of log lines stream.
        :param url: base URL of Socket.IO server
        :param socketio_path: The endpoint where the Socket.IO server is installed.
        :param resource_properties: metadata of a resource being monitored (properties to identify a Job)
        :param on_next_line: callback function called whenever a new line is consumed.
        """
        self.url = url
        self.socketio_path = socketio_path
        self.resource_properties = resource_properties
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
        def logs_nextline(data):
            """"Event for retrieveing a new log line"""
            on_next_line(data.get('line'))
            return True

    def _subscribe_for_logs(self):
        self.sio.call('subscribe_for_logs', {
            'resource_properties': self.resource_properties,
        })

    @contextlib.contextmanager
    def connect_async(self):
        """Set up and tear down a client context consuming logs in background"""
        self.sio.connect(self.url, socketio_path=self.socketio_path)
        self._subscribe_for_logs()
        try:
            threading.Thread(
                target=lambda: self.sio.wait(),
                daemon=True,
            ).start()
            yield
        finally:
            self.sio.disconnect()

    def connect_and_wait(self):
        """Connect to a server synchronously and listen for the logs"""
        try:
            self.sio.connect(self.url, socketio_path=self.socketio_path)
            self._subscribe_for_logs()
            self.sio.wait()
        except KeyboardInterrupt:
            self.sio.disconnect()
