import time

from fastapi import FastAPI, Request, Response
import anyio
from starlette.types import ASGIApp, Receive, Scope, Send, Message

from racetrack_client.log.logs import get_logger
from racetrack_commons.api.asgi.asgi_server import HIDDEN_ACCESS_LOGS
from racetrack_commons.api.metrics import metric_request_duration, metric_requests_done, metric_requests_started
from racetrack_commons.api.tracing import get_caller_header_name, get_tracing_header_name, RequestTracingLogger

logger = get_logger(__name__)

# Don't print these access logs if occurred
HIDDEN_REQUEST_LOGS = {
    'GET /live',
    'GET /live/',
    'GET /ready',
    'GET /ready/',
    'GET /health',
    'GET /health/',
    'GET /metrics',
    'GET /metrics/',
}


def enable_request_access_log(fastapi_app: FastAPI):
    """Log every incoming request right after it's received with its Tracing ID"""
    fastapi_app.add_middleware(RequestAccessLogMiddleware)


def enable_response_access_log(fastapi_app: FastAPI):
    """Log every response right after it's finished with its status code and Tracing ID"""
    fastapi_app.add_middleware(ResponseAccessLogMiddleware)


class RequestAccessLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app: ASGIApp = app
        self.tracing_header: str = get_tracing_header_name()
        self.caller_header: str = get_caller_header_name()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope=scope)
        tracing_id = request.headers.get(self.tracing_header)
        caller_name = request.headers.get(self.caller_header)
        uri = request.url.replace(scheme='', netloc='')
        request_logger = RequestTracingLogger(logger, {
            'tracing_id': tracing_id,
            'caller_name': caller_name,
        })
        message = f'{request.method} {uri}'
        if message not in HIDDEN_REQUEST_LOGS:
            request_logger.debug(f'Request: {message}')

        await self.app(scope, receive, send)


class ResponseAccessLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app: ASGIApp = app
        self.tracing_header: str = get_tracing_header_name()
        self.caller_header: str = get_caller_header_name()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope=scope)
        method = request.method
        uri = request.url.replace(scheme='', netloc='')

        async def send_extra(message: Message):

            if await is_request_disconnected(receive):
                logger.error(f"Request cancelled by the client: {method} {uri}")
                response = Response(status_code=204)  # No Content
                return await response(scope, receive, send)

            if message["type"] == "http.response.start":
                response_code: int = message['status']
                log_line = f'{method} {uri} {response_code}'

                if log_line not in HIDDEN_ACCESS_LOGS:
                    request_logger = RequestTracingLogger(logger, {
                        'tracing_id': request.headers.get(self.tracing_header),
                        'caller_name': request.headers.get(self.caller_header),
                    })
                    request_logger.info(log_line)

            await send(message)

        metric_requests_started.inc()
        start_time = time.time()
        try:
            await self.app(scope, receive, send_extra)

        except RuntimeError as exc:
            if str(exc) == 'No response returned.':
                if await is_request_disconnected(receive):
                    tracing_id = request.headers.get(self.tracing_header)
                    if tracing_id is not None:
                        logger.error(f"[{tracing_id}] Request cancelled by the client: {method} {uri}")
                    else:
                        logger.error(f"Request cancelled by the client: {method} {uri}")
                    response = Response(status_code=204)  # No Content
                    return await response(scope, receive, send)
            raise
        finally:
            metric_request_duration.observe(time.time() - start_time)
            metric_requests_done.inc()


async def is_request_disconnected(receive: Receive) -> bool:
    # If message isn't immediately available, move on
    with anyio.CancelScope() as cs:
        cs.cancel()
        message = await receive()
        if message.get("type") == "http.disconnect":
            return True
    return False
