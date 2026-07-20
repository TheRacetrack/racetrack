from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount
from starlette.types import ASGIApp, Receive, Scope, Send

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class ASGIReloader:
    """
    ASGI wrapper allowing to replace the application on the run without restarting the server
    """

    def __init__(self):
        main_app = FastAPI()
        main_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.main_app = main_app
        self.subapp: Optional[ASGIApp] = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.main_app(scope, receive, send)

    def mount(self, subapp: ASGIApp):
        self.unmount_all()
        self.subapp = subapp
        self.main_app.mount("/", subapp, name='_root_app')

    def unmount_all(self):
        self.main_app.router.routes = []

    def unmount_root_app(self):
        routes = self.main_app.router.routes
        for index, route in enumerate(routes):
            if isinstance(route, Mount):
                if route.path == "" and route.name == '_root_app':
                    routes.pop(index)
                    return
        logger.warning("Couldn't find root ASGI app to unmount")
