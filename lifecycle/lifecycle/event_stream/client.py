import contextlib
import json
import threading
from typing import Callable

from websockets.sync.client import connect, ClientConnection
from websockets.exceptions import ConnectionClosedOK

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class EventStreamClient:
    def __init__(
        self,
        url: str,
        on_event: Callable[[dict], None],
    ):
        self.url = url
        self.on_event = on_event
        self.should_exit = False
        self.websocket: ClientConnection | None = None

    @contextlib.contextmanager
    def connect_async(self):
        with connect(self.url) as websocket:
            self.websocket = websocket
            threading.Thread(
                target=lambda: self.receive_loop(),
                daemon=True,
            ).start()
            yield

    def receive_loop(self):
        while not self.should_exit:
            try:
                raw_message: str = self.websocket.recv()
                message = json.loads(raw_message)
                self.on_event(message)
            except ConnectionClosedOK:
                return
