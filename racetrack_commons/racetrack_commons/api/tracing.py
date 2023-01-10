import os
import logging
from fastapi import Request

from racetrack_client.log.exception import get_exc_info_details
from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


class RequestTracingLogger(logging.LoggerAdapter):
    """Logging adapter adding request tracing ID to log messages"""
    def process(self, msg, kwargs):
        tracing_id = self.extra['tracing_id']
        if tracing_id is None:
            return msg, kwargs
        else:
            return f"[{tracing_id}] {msg}", kwargs


def get_tracing_header_name() -> str:
    """Return name of HTTP request header that contains the tracing ID"""
    return os.environ.get('REQUEST_TRACING_HEADER', 'X-Request-Tracing-Id')


def log_request_exception_with_tracing(request: Request, e: BaseException):
    try:
        ex_type, e, tb = (type(e), e, e.__traceback__)
        log_message = get_exc_info_details(ex_type, e, tb)

        tracing_header = get_tracing_header_name()
        tracing_id = request.headers.get(tracing_header)
        request_logger = RequestTracingLogger(logger, {'tracing_id': tracing_id})
        request_logger.error(log_message)
        
    except BaseException as e:
        logger.exception(e)
