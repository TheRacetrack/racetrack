import asyncio
import threading

import socketio
import time

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class EventStreamServer:
    def __init__(self):
        """Socket.IO server for streaming events to clients"""
        self.sio = socketio.AsyncServer(async_mode='asgi')
        self.clients: list[str] = []  # List of Client IDs
        self.watcher_thread: threading.Thread | None = None

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
        while len(self.clients) > 0:
            logger.debug('Periodic database check for new events')
            time.sleep(5_000)

        logger.debug('Stopping watcher thread in Event Streamer')
