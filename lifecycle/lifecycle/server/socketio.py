import contextlib
import threading
from abc import ABC

import socketio
from werkzeug.serving import make_server
from pydantic import BaseModel

from lifecycle.config import Config
from lifecycle.infrastructure.infra_target import get_infrastructure_target
from lifecycle.job.registry import read_versioned_job
from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger
from lifecycle.monitor.base import LogsStreamer
from racetrack_commons.entities.dto import JobDto

logger = get_logger(__name__)


class LogSessionDetails(BaseModel, arbitrary_types_allowed=True):
    client_id: str
    job_name: str
    job_version: str
    session_id: str
    logs_streamer: LogsStreamer


class JobRetriever(ABC):
    def get_job(self, job_name: str, job_version: str) -> JobDto:
        raise NotImplementedError()


class RegistryJobRetriever(JobRetriever):
    def __init__(self, config: Config):
        self.config = config

    def get_job(self, job_name: str, job_version: str) -> JobDto:
        return read_versioned_job(job_name, job_version, self.config)


class SocketIOServer:
    def __init__(self, job_retriever: JobRetriever):
        """
        Socket.IO server for streaming data to clients
        """
        self.sio = socketio.Server(async_mode='threading')
        self.log_sessions_by_client: dict[str, LogSessionDetails] = {}  # Map Client ID to session details
        self.log_sessions_by_id: dict[str, LogSessionDetails] = {}  # Map Session ID to session details
        self.job_retriever: JobRetriever = job_retriever

        @self.sio.event
        def connect(client_id: str, environ):
            logger.debug(f'Client {client_id} connected to Socket.IO')

        @self.sio.event
        def subscribe_for_logs(client_id: str, data: dict) -> str:
            """Request new logs session from a server and listen on the events from it"""
            try:
                if client_id in self.log_sessions_by_client:
                    return self.log_sessions_by_client[client_id].session_id
                else:
                    resource_properties = data.get('resource_properties', {})
                    return self.open_logs_session(client_id, resource_properties)
            except BaseException as e:
                log_exception(e)

        @self.sio.event
        def disconnect(client_id: str):
            if client_id in self.log_sessions_by_client:
                self.close_logs_session(self.log_sessions_by_client[client_id])
            logger.debug(f'Client {client_id} disconnected from Socket.IO')

        self.wsgi_app = socketio.WSGIApp(self.sio, socketio_path='lifecycle/socket.io')

    def open_logs_session(self, client_id: str, resource_properties: dict[str, str]) -> str:
        logger.info(f'Creating log session for client: {client_id}')
        job_name = resource_properties['job_name']
        job_version = resource_properties['job_version']
        job = self.job_retriever.get_job(job_name, job_version)
        job_version = job.version  # resolve version alias
        session_id = f'{client_id}_{job_name}_{job_version}'

        infrastructure = get_infrastructure_target(job.infrastructure_target)

        session = LogSessionDetails(
            client_id=client_id,
            job_name=job_name,
            job_version=job_version,
            session_id=session_id,
            logs_streamer=infrastructure.logs_streamer,
        )
        self.log_sessions_by_client[client_id] = session
        self.log_sessions_by_id[session_id] = session

        infrastructure.logs_streamer.create_session(session_id, resource_properties={
            'job_name': job_name,
            'job_version': job_version,
        }, on_next_line=self.broadcast_logs_nextline)
        return session_id

    def close_logs_session(self, session: LogSessionDetails):
        session.logs_streamer.close_session(session.session_id)
        del self.log_sessions_by_client[session.client_id]
        del self.log_sessions_by_id[session.session_id]
        logger.info(f'Log session closed: {session.session_id}')

    @staticmethod
    def _get_session_id(client_id: str, job_name: str, job_version: str) -> str:
        return f'{client_id}_{job_name}_{job_version}'

    def broadcast_logs_nextline(self, session_id: str, message: str):
        session = self.log_sessions_by_id[session_id]
        self.sio.call('logs_nextline', {
            'line': message,
        }, to=session.client_id)

    def disconnect_all(self):
        for client_id in list(self.log_sessions_by_client.keys()):
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
