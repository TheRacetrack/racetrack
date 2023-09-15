from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from exceptiongroup import ExceptionGroup


def mount_at_base_path(api_app: ASGIApp, *base_path_patterns: str) -> FastAPI:
    wrapper_app = FastAPI()
    wrapper_app.router.routes = []

    for base_path_pattern in base_path_patterns:
        @wrapper_app.get(base_path_pattern)
        async def _base_path_redirect(request: Request):
            return RedirectResponse(f"{request.url.path}/")

        wrapper_app.mount(base_path_pattern, api_app)

    wrapper_app.mount('/', api_app)
    wrapper_app.add_middleware(TrailingSlashForwarder)
    return wrapper_app


class TrailingSlashForwarder:
    forwarded_paths: set = set()

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope['path']
        if path in self.forwarded_paths and not path.endswith('/'):
            scope['path'] = f"{path}/"
            scope['raw_path'] = scope['path'].encode()
        try:
            await self.app(scope, receive, send)
        except ExceptionGroup as e:
            for ex in e.exceptions:
                print(ex)
            raise e
        except BaseException as e:
            print(e)
            raise e

    @classmethod
    def mount_path(cls, path: str):
        cls.forwarded_paths.add(path)
