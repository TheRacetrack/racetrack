import os
import traceback
from typing import Collection, Iterable

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)


def short_exception_logger(exc_info, *_):
    """
    Display excpetion traceback in concise one-line format.
    Avoid printing long, superfluous lines of traceback, especially for multi-cause exceptions.
    """
    try:
        ex_type, e, tb = exc_info
        log_message = get_exc_info_details(ex_type, e, tb)
        logger.error(log_message)
    except BaseException as e:
        logger.exception(e)


def get_exc_info_details(ex_type, e, tb) -> str:
    """
    Return concise one-line details of exception, containing message, traceback and root cause type
    :param ex_type: Exception type
    :param e: Exception instance
    :param tb: Traceback object
    """
    traceback_ex = traceback.TracebackException(ex_type, e, tb, limit=None)
    traceback_lines = list(_get_traceback_lines(traceback_ex))
    traceback_str = ', '.join(traceback_lines)
    cause = _root_cause_type(e)
    return f'{str(e).strip()}, cause={cause}, traceback={traceback_str}'


def _root_cause_type(e: BaseException) -> str:
    while e.__cause__ is not None:
        e = e.__cause__
    return type(e).__name__


def log_exception(e: BaseException):
    """
    Log exception in concise one-line format containing message, exception type and short traceback
    """
    exc_info = (type(e), e, e.__traceback__)
    short_exception_logger(exc_info)


def short_exception_details(e: BaseException) -> str:
    """
    Return concise one-line details of exception, containing message, traceback and root cause type
    """
    return get_exc_info_details(type(e), e, e.__traceback__)


def _get_traceback_lines(t1: traceback.TracebackException) -> Iterable[str]:
    while True:
        frames: Collection[traceback.FrameSummary] = t1.stack
        for frame in frames:
            yield f'{os.path.normpath(frame.filename)}:{frame.lineno}'

        if t1.__cause__ is None:
            break
        t1 = t1.__cause__
