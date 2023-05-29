import asyncio
import threading

import socketio
import time

from lifecycle.config import Config
from lifecycle.job.registry import list_job_registry
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import JobDto

logger = get_logger(__name__)


class EventStreamServer:
    def __init__(self, config: Config):
        """Socket.IO server for streaming events to clients"""
        self.sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
        self.clients: list[str] = []  # List of Client IDs
        self.watcher_thread: threading.Thread | None = None
        self.config = config

        @self.sio.event
        async def connect(client_id: str, environ):
            logger.debug(f'Client {client_id} connected to Event Streamer')
            self.clients.append(client_id)
            await self.sio.emit('connected', {}, to=client_id)
            if len(self.clients) > 0 and (self.watcher_thread is None or not self.watcher_thread.is_alive()):
                self.watcher_thread = threading.Thread(target=self.watch_database_events, args=(), daemon=True)
                self.watcher_thread.start()

        @self.sio.event
        async def disconnect(client_id: str):
            logger.debug(f'Client {client_id} disconnected from Event Streamer')
            if client_id in self.clients:
                self.clients.remove(client_id)

        @self.sio.on('*')
        async def catch_all(event, sid, data):
            logger.warning(f'Unhandled Socket.IO event: {event}, {sid}, {data}')

        self.asgi_app = socketio.ASGIApp(self.sio, socketio_path='lifecycle/socketio/events')

    async def notify_clients_async(self, event: dict):
        for client_id in self.clients.copy():
            # emit doesn't wait for the response
            await self.sio.emit('broadcast_event', event, to=client_id)

    def notify_clients(self, event: dict):
        asyncio.run(self.notify_clients_async(event))

    async def disconnect_all(self):
        for client_id in self.clients.copy():
            await self.sio.disconnect(client_id, ignore_queue=True)

    def watch_database_events(self):
        logger.debug('Starting watcher thread in Event Streamer')
        last_jobs: dict[str, JobDto] | None = None
        while len(self.clients) > 0:

            jobs = list_job_registry(self.config)
            current_jobs: dict[str, JobDto] = {job.id: job for job in jobs}
            if last_jobs is not None and current_jobs != last_jobs:
                logger.debug(f'Detected change in job models')
                self.notify_clients({
                    'event': 'job_models_changed',
                })
            last_jobs = current_jobs

            time.sleep(self.config.job_watcher_interval)
        logger.debug('Stopping watcher thread in Event Streamer')
