import os
import logging

from fastapi import Request
from exceptiongroup import ExceptionGroup

from racetrack_client.log.exception import get_exc_info_details
from racetrack_client.log.logs import logger


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

        ex_type, e, tb = (type(e), e, e.__traceback__)
        log_message = get_exc_info_details(ex_type, e, tb)

        tracing_header = get_tracing_header_name()
        caller_header = get_caller_header_name()
        tracing_id = request.headers.get(tracing_header)
        caller_name = request.headers.get(caller_header)
        request_logger = logger.bind(tracing_id=tracing_id, caller_name=caller_name)
        request_logger.error(log_message)

    except BaseException as e:
        root_logger = logging.getLogger('racetrack')
        root_logger.error("Handler failed to process an exception")
        root_logger.exception(e)
