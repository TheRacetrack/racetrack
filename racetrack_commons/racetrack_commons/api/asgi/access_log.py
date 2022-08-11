from fastapi import FastAPI, Request, Response

from racetrack_client.log.logs import get_logger
from racetrack_commons.api.asgi.asgi_server import HIDDEN_ACCESS_LOGS
from racetrack_commons.api.tracing import RequestTracingLogger, get_tracing_header_name

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
    tracing_header = get_tracing_header_name()

    @fastapi_app.middleware('http')
    async def access_log_on_receive(request: Request, call_next) -> Response:
        tracing_id = request.headers.get(tracing_header)
        uri = request.url.replace(scheme='', netloc='')
        request_logger = RequestTracingLogger(logger, {'tracing_id': tracing_id})
        message = f'{request.method} {uri}'
        if message not in HIDDEN_REQUEST_LOGS:
            request_logger.debug(f'Request: {message}')
        return await call_next(request)


def enable_response_access_log(fastapi_app: FastAPI):
    tracing_header = get_tracing_header_name()

    @fastapi_app.middleware('http')
    async def access_log(request: Request, call_next) -> Response:
        try:
            response: Response = await call_next(request)
        except RuntimeError as exc:
            if str(exc) == 'No response returned.':
                if await request.is_disconnected():
                    tracing_id = request.headers.get(tracing_header)
                    method = request.method
                    uri = request.url.replace(scheme='', netloc='')
                    if tracing_id is not None:
                        logger.error(f"[{tracing_id}] Request cancelled by the client: {method} {uri}")
                    else:
                        logger.error(f"Request cancelled by the client: {method} {uri}")
                    return Response(status_code=204)  # No Content
            raise

        method = request.method
        uri = request.url.replace(scheme='', netloc='')
        response_code = response.status_code
        log_line = f'{method} {uri} {response_code}'

        if log_line not in HIDDEN_ACCESS_LOGS:
            tracing_id = request.headers.get(tracing_header)
            if tracing_id is not None:
                logger.info(f"[{tracing_id}] {log_line}")
            else:
                logger.info(log_line)
        
        return response
