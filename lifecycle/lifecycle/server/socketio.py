from __future__ import annotations
import contextlib
import threading
from typing import Dict

import socketio
from werkzeug.serving import make_server

from lifecycle.monitor.base import LogsStreamer
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class SocketIOServer:
    def __init__(self, log_streamers: list[LogsStreamer]):
        """
        Socket.IO server for streaming data to clients
        :param logs_streamer: Source of logs
        """
        self.sio = socketio.Server(async_mode='threading')
        self.client_resources: Dict[str, Dict[str, str]] = {}  # Map Client ID to a resource
        for log_streamer in log_streamers:
            log_streamer.broadcaster = self.broadcast_logs_nextline

        @self.sio.event
        def connect(client_id: str, environ):
            logger.debug(f'Client {client_id} connected to Socket.IO')

        @self.sio.event
        def subscribe_for_logs(client_id: str, data: Dict) -> str:
            """Request new logs session from a server and listen on the events from it"""
            resource_properties = data.get('resource_properties', {})
            if client_id in self.client_resources:
                resource_properties = self.client_resources[client_id]
                return self.get_session_id(client_id, resource_properties)
            else:
                self.client_resources[client_id] = resource_properties
                session_id = self.get_session_id(client_id, resource_properties)
                logger.info(f'Creating consumer session: {session_id}')
                for log_streamer in log_streamers:
                    log_streamer.create_session(session_id, resource_properties)
                return session_id

        @self.sio.event
        def disconnect(client_id: str):
            logger.debug(f'Client {client_id} disconnected from Socket.IO')
            if client_id in self.client_resources:
                resource_properties = self.client_resources[client_id]
                del self.client_resources[client_id]
                session_id = self.get_session_id(client_id, resource_properties)
                logger.info(f'Consumer session closed: {session_id}')
                for log_streamer in log_streamers:
                    log_streamer.close_session(session_id)

        self.wsgi_app = socketio.WSGIApp(self.sio, socketio_path='lifecycle/socket.io')

    @staticmethod
    def get_session_id(client_id: str, resource_properties: Dict[str, str]) -> str:
        job_name = resource_properties.get('job_name')
        job_version = resource_properties.get('job_version')
        return f'{client_id}_{job_name}_{job_version}'

    def broadcast_logs_nextline(self, session_id: str, message: str):
        for client_id, resource_properties in self.client_resources.copy().items():
            _session_id = self.get_session_id(client_id, resource_properties)
            if _session_id == session_id:
                self.sio.call('logs_nextline', {
                    'line': message,
                }, to=client_id)

    def disconnect_all(self):
        for client_id in list(self.client_resources.keys()):
            self.sio.disconnect(client_id, ignore_queue=True)

    @contextlib.contextmanager
    def run_async(self, port: int):
        """Set up and tear down a server context in background"""
        srv = make_server('0.0.0.0', port, self.wsgi_app, threaded=True)
        try:
            threading.Thread(
                target=lambda: srv.serve_forever(),
                daemon=True,
            ).start()
            yield
        finally:
            self.disconnect_all()
            srv.shutdown()
