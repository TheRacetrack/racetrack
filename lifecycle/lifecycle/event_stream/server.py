import asyncio
import threading
import time
import warnings

warnings.filterwarnings(
    action='ignore',
    category=DeprecationWarning,
    module=r'falcon.media'
)
from falcon import Request
from falcon.asgi import WebSocket, App

from lifecycle.config import Config
from lifecycle.job.registry import list_job_registry
from lifecycle.server.metrics import metric_event_stream_client_connected, metric_event_stream_client_disconnected
from racetrack_client.log.logs import get_logger
from racetrack_commons.entities.dto import JobDto

logger = get_logger(__name__)


class EventStreamServer:
    def __init__(self, config: Config):
        """Socket.IO server for streaming events to clients"""
        self.config = config
        self.clients: list[WebSocket] = []
        self.watcher_thread: threading.Thread | None = None
        server = self

        class WebSocketResource:
            async def on_websocket(self, _: Request, ws: WebSocket):
                await ws.accept()
                logger.debug(f'Client connected to Event Stream')
                metric_event_stream_client_connected.inc()
                server.clients.append(ws)

                try:
                    if server.watcher_thread is None or not server.watcher_thread.is_alive():
                        server.watcher_thread = threading.Thread(target=server.watch_database_events, args=(), daemon=True)
                        server.watcher_thread.start()

                    while True:
                        message: str = await ws.receive_text()
                        logger.debug(f'Received websocket message: {message}')

                finally:
                    logger.debug(f'Client disconnected from Event Stream')
                    metric_event_stream_client_disconnected.inc()
                    server.clients.remove(ws)

        self.asgi_app = App()
        self.asgi_app.add_route('/lifecycle/websocket/events', WebSocketResource())

    async def notify_clients_async(self, event: dict):
        logger.debug(f'Notifying all Event Stream clients: {len(self.clients)}')
        for ws in self.clients.copy():
            await ws.send_media(event)

    def notify_clients(self, event: dict):
        asyncio.run(self.notify_clients_async(event))

    def watch_database_events(self):
        logger.debug('Starting watcher thread in Event Stream')
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

        logger.debug('Event Stream watcher thread stopped')
