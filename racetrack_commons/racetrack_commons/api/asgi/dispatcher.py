from typing import Callable, Awaitable
from starlette.types import ASGIApp, Receive, Scope, Send

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class AsgiDispatcher:
    def __init__(self, patterns: dict[str, ASGIApp], default: ASGIApp, on_startup: Callable[[], Awaitable[None]] | None = None):
        self.patterns = patterns
        self.default_app = default
        self.on_startup = on_startup

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] == 'lifespan' and self.on_startup is not None:
            message = await receive()
            print(f'AsgiDispatcher: lifespan: message.type: {message["type"]}')
            if message['type'] == 'lifespan.startup':
                await self.on_startup()
                await send({'type': 'lifespan.startup.complete'})
                return
            if message['type'] == 'lifespan.shutdown':
                logger.debug('ASGI shutdown event')

        app = None
        request_path = scope['path']
        for pattern_prefix, pattern_app in self.patterns.items():
            if request_path.startswith(pattern_prefix):
                if scope['type'] in {'http', 'websocket'}:
                    app = pattern_app
                    break

        if app is None:
            app = self.default_app
        await app(scope, receive, send)
