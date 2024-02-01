import os
import traceback
from typing import Collection, Iterable, Tuple

from racetrack_client.log.logs import get_logger

logger = get_logger(__name__)

PRINT_FULL_TRACEBACK = False


def log_exception(e: BaseException):
    """
    Log exception in concise one-line format containing message, exception type and short traceback
    """
    try:
        error_message, cause, tb = exception_details(e)
        logger.error(error_message, extra={'cause': cause, 'traceback': tb})
        if PRINT_FULL_TRACEBACK:
            traceback.print_exception(e)
    except BaseException as e:
        logger.exception(str(e))


def exception_details(e: BaseException) -> Tuple[str, str, str]:
    """
    Return concise details of exception: message, root cause type and one-line details traceback
    :param e: Exception instance
    :return Tuple of: message string, root cause type and traceback
    """
    traceback_ex = traceback.TracebackException(type(e), e, e.__traceback__, limit=None)
    traceback_lines = list(_get_traceback_lines(traceback_ex))
    traceback_str = ', '.join(traceback_lines)
    cause = _root_cause_type(e)
    error_msg = str(e).strip()
    return error_msg, cause, traceback_str


def short_exception_details(e: BaseException) -> str:
    """
    Return concise one-line details of exception, containing message, traceback and root cause type
    """
    error_message, cause, tb = exception_details(e)
    return f'{error_message}, cause={cause}, traceback={tb}'


def _root_cause_type(e: BaseException) -> str:
    while e.__cause__ is not None:
        e = e.__cause__
    return type(e).__name__


def _get_traceback_lines(t1: traceback.TracebackException) -> Iterable[str]:
    while True:
        frames: Collection[traceback.FrameSummary] = t1.stack
        for frame in frames:
            yield f'{os.path.normpath(frame.filename)}:{frame.lineno}'

        if t1.__cause__ is None:
            break
        t1 = t1.__cause__
