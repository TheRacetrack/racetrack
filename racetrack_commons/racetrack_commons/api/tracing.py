import os
import logging

from fastapi import Request
from exceptiongroup import ExceptionGroup

from racetrack_client.log.exception import exception_details
from racetrack_client.log.logs import get_logger
from racetrack_client.utils.env import is_env_flag_enabled

logger = get_logger(__name__)


class RequestTracingLogger(logging.LoggerAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.caller_enabled = is_env_flag_enabled('LOG_CALLER_NAME')

    """Logging adapter adding request tracing ID to log messages"""
    def process(self, msg, kwargs):
        extra = kwargs.get('extra', {})

        tracing_id = self.extra['tracing_id']
        caller_name = self.extra.get('caller_name')
        if tracing_id:
            extra['tracing_id'] = tracing_id
        if caller_name and self.caller_enabled:
            extra['caller_name'] = caller_name

        kwargs['extra'] = extra
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
            eg: ExceptionGroup = e
            for suberror in eg.exceptions:
                log_request_exception_with_tracing(request, suberror)
            if len(eg.exceptions) == 1:
                return

        log_message, cause, traceback = exception_details(e)

        tracing_header = get_tracing_header_name()
        caller_header = get_caller_header_name()
        tracing_id = request.headers.get(tracing_header)
        caller_name = request.headers.get(caller_header)
        request_logger = RequestTracingLogger(logger, {
            'tracing_id': tracing_id,
            'caller_name': caller_name,
        })
        request_logger.error(log_message, extra={'cause': cause, 'traceback': traceback})

    except BaseException as e:
        root_logger = logging.getLogger('racetrack')
        root_logger.error("Handler failed to process an exception")
        root_logger.exception(str(e))
