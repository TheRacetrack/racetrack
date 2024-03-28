from typing import Dict
from starlette.types import ASGIApp, Receive, Scope, Send


class AsgiDispatcher:
    def __init__(self, patterns: Dict[str, ASGIApp], default: ASGIApp):
        self.patterns = patterns
        self.default_app = default

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
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
