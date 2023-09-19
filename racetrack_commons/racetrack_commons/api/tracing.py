import os
import logging

from fastapi import Request
from exceptiongroup import ExceptionGroup

from racetrack_client.log.exception import get_exc_info_details
from racetrack_client.log.logs import get_logger
from racetrack_commons.api.debug import is_env_flag_enabled

logger = get_logger(__name__)


class RequestTracingLogger(logging.LoggerAdapter):
    """Logging adapter adding request tracing ID to log messages"""
    def process(self, msg, kwargs):
        tracing_id = self.extra['tracing_id']
        caller_name = self.extra.get('caller_name')
        caller_enabled = is_env_flag_enabled('LOG_CALLER_NAME')
        if tracing_id and caller_name and caller_enabled:
            return f"[{tracing_id}] <{caller_name}> {msg}", kwargs
        elif tracing_id:
            return f"[{tracing_id}] {msg}", kwargs
        elif caller_name and caller_enabled:
            return f"<{caller_name}> {msg}", kwargs
        else:
            return msg, kwargs


def get_tracing_header_name() -> str:
    """Return name of HTTP request header that contains the tracing ID"""
    return os.environ.get('REQUEST_TRACING_HEADER', 'X-Request-Tracing-Id')


def get_caller_header_name() -> str:
    """Return name of HTTP request header that contains the caller name"""
    return os.environ.get('CALLER_NAME_HEADER', 'X-Caller-Name')


def log_request_exception_with_tracing(request: Request, e: BaseException):
    try:
        if isinstance(e, ExceptionGroup):
            for suberror in e.exceptions:
                log_request_exception_with_tracing(request, suberror)

        ex_type, e, tb = (type(e), e, e.__traceback__)
        log_message = get_exc_info_details(ex_type, e, tb)

        tracing_header = get_tracing_header_name()
        caller_header = get_caller_header_name()
        tracing_id = request.headers.get(tracing_header)
        caller_name = request.headers.get(caller_header)
        request_logger = RequestTracingLogger(logger, {
            'tracing_id': tracing_id,
            'caller_name': caller_name,
        })
        request_logger.error(log_message)
        
    except BaseException as e:
        logger.exception(e)
