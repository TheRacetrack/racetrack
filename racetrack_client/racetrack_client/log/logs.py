import json
import logging
import os
import sys
from typing import Optional, Dict, Any

from racetrack_client.utils.env import is_env_flag_enabled
from racetrack_client.utils.strings import strip_ansi_colors
from racetrack_client.utils.time import timestamp_to_iso8601

LOG_FORMAT = '\033[2m[%(asctime)s]\033[0m %(levelname)s %(message)s'
LOG_FORMAT_DEBUG = '\033[2m[%(asctime)s]\033[0m %(name)s %(filename)s %(lineno)s %(levelname)s %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
ISO_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

structured_logs_on: bool = is_env_flag_enabled('LOG_STRUCTURED', 'false')
log_caller_enabled: bool = is_env_flag_enabled('LOG_CALLER_NAME', 'false')

logger: logging.Logger = logging.getLogger('racetrack')


def configure_logs(log_level: Optional[str] = None):
    """Configure root logger with a log level"""
    log_level = log_level or os.environ.get('LOG_LEVEL', 'debug')
    level = _parse_logging_level(log_level)
    # Set root level to INFO to avoid printing a ton of garbage DEBUG logs from imported libraries
    logging.basicConfig(stream=sys.stdout, format=LOG_FORMAT, level=logging.INFO, datefmt=LOG_DATE_FORMAT, force=True)

    original_formatter = logging.getLogger().handlers[0].formatter
    if structured_logs_on:
        formatter = StructuredFormatter()
    else:
        formatter = ColoredFormatter(original_formatter)
    set_logging_formatter(formatter)

    root_logger = logging.getLogger('racetrack')
    root_logger.setLevel(level)


def get_logger(_logger_name: str) -> logging.Logger:
    """Get configured racetrack logger"""
    return logging.getLogger('racetrack').getChild(_logger_name)


def set_logging_formatter(formatter: logging.Formatter):
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)


def _format_extra_vars(extra: Dict[str, Any]) -> str:
    if len(extra) == 0:
        return ''
    keys = extra.keys()
    parts = [_format_extra_var(key, extra[key]) for key in keys]
    return ', '.join(parts)


def _format_extra_var(var: str, val: Any) -> str:
    val = str(val)
    if ' ' in val:
        return f'{var}="{val}"'
    else:
        return f'{var}={val}'


def _parse_logging_level(str_level: str) -> int:
    return {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL,
        'off': logging.NOTSET,
    }[str_level.lower()]


class ColoredFormatter(logging.Formatter):
    def __init__(self, plain_formatter):
        logging.Formatter.__init__(self)
        self.plain_formatter = plain_formatter

    def format(self, record: logging.LogRecord) -> str:
        if record.levelname in self.log_level_templates:
            record.levelname = self.log_level_templates[record.levelname].format(record.levelname)

        record_dict = record.__dict__
        extra: Dict[str, Any] = record_dict.get('extra') or {}

        if record_dict.get('cause'):
            extra['cause'] = record_dict.get('cause')
        if record_dict.get('traceback'):
            extra['traceback'] = record_dict.get('traceback')
        if record_dict.get('tracing_id'):
            extra['tracing_id'] = record_dict.get('tracing_id')
        if record_dict.get('caller_name'):
            extra['caller_name'] = record_dict.get('caller_name')

        line = self.plain_formatter.format(record)
        if extra:
            return line + ', ' + _format_extra_vars(extra)

        return line

    log_level_templates = {
        'CRITICAL': '\033[1;31mCRIT \033[0m',
        'ERROR': '\033[1;31mERROR\033[0m',
        'WARNING': '\033[0;33mWARN \033[0m',
        'INFO': '\033[0;34mINFO \033[0m',
        'DEBUG': '\033[0;32mDEBUG\033[0m',
    }


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        time: str = timestamp_to_iso8601(record.created)
        level: str = record.levelname
        message: str = strip_ansi_colors(record.msg)

        record_dict = record.__dict__
        extra: Dict[str, Any] = record_dict.get('extra') or {}

        log_rec = {
            "time": time,
            "lvl": level,
            "msg": message,
            **extra,
        }

        if record_dict.get('cause'):
            log_rec['cause'] = record_dict.get('cause')
        if record_dict.get('traceback'):
            log_rec['traceback'] = record_dict.get('traceback')
        if record_dict.get('tracing_id'):
            log_rec['tracing_id'] = record_dict.get('tracing_id')
        if record_dict.get('caller_name'):
            log_rec['caller_name'] = record_dict.get('caller_name')

        if record.exc_info and record.exc_text is None:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            log_rec["exc_info"] = record.exc_text
        if record.stack_info:
            log_rec["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(log_rec)
