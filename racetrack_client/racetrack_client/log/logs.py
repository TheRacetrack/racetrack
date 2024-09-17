import json
import logging
import os
from datetime import datetime
import time

import sys
from typing import Optional, Dict, Any

from racetrack_client.utils.env import is_env_flag_enabled
from racetrack_client.utils.strings import strip_ansi_colors
from racetrack_client.utils.time import timestamp_to_iso8601

LOG_FORMAT = '\033[2m[%(asctime)s]\033[0m %(levelname)s %(message)s'
LOG_FORMAT_DEBUG = '\033[2m[%(asctime)s]\033[0m %(levelname)s %(name)s:%(lineno)s %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
ISO_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

structured_logs_on: bool = is_env_flag_enabled('LOG_STRUCTURED', 'false')
log_caller_enabled: bool = is_env_flag_enabled('LOG_CALLER_NAME', 'false')
debug_format_enabled: bool = is_env_flag_enabled('LOG_FORMAT_DEBUG', 'false')

logger: logging.Logger = logging.getLogger('racetrack')


def configure_logs(log_level: Optional[str] = None):
    """Configure root logger with a log level"""
    log_level = log_level or os.environ.get('LOG_LEVEL', 'debug')
    level = _parse_logging_level(log_level)
    # Set root level to INFO to avoid printing a ton of garbage DEBUG logs from imported libraries
    log_format = LOG_FORMAT_DEBUG if debug_format_enabled else LOG_FORMAT
    logging.basicConfig(stream=sys.stdout, format=log_format, level=logging.INFO, datefmt=LOG_DATE_FORMAT, force=True)

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

    log_level_templates = {
        'CRITICAL': '\033[1;31mCRIT \033[0m',
        'ERROR': '\033[1;31mERROR\033[0m',
        'WARNING': '\033[0;33mWARN \033[0m',
        'INFO': '\033[0;34mINFO \033[0m',
        'DEBUG': '\033[0;32mDEBUG\033[0m',
    }

    def format(self, record: logging.LogRecord) -> str:
        part_time = self.format_time()
        part_levelname = self.log_level_templates.get(record.levelname, record.levelname)
        log_message: str = record.getMessage()
        logger_details = self._logger_details(record)
        if logger_details:
            line = f'{part_time} {part_levelname} {logger_details}: {log_message}'
        else:
            line = f'{part_time} {part_levelname} {log_message}'

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
        if extra:
            line += ', ' + _format_extra_vars(extra)

        if not sys.stdout.isatty():
            line = strip_ansi_colors(line)
        return line

    def format_time(self) -> str:
        now_tz = datetime.now().astimezone()
        if time.timezone == 0:
            time_formatted = now_tz.strftime('%Y-%m-%d %H:%M:%SZ')
        else:
            time_formatted = now_tz.strftime('%Y-%m-%d %H:%M:%S')
        return f'\033[2m[{time_formatted}]\033[0m'

    def _logger_details(self, record: logging.LogRecord) -> Optional[str]:
        logger_name = record.name
        if debug_format_enabled or not logger_name.startswith('racetrack'):
            return f'{logger_name}:{record.lineno}'
        else:
            return None


class StructuredFormatter(logging.Formatter):
    def __init__(self, **kwargs):
        logging.Formatter.__init__(self)

    def format(self, record: logging.LogRecord) -> str:
        time_str: str = timestamp_to_iso8601(record.created)
        level: str = record.levelname
        message: str = strip_ansi_colors(record.msg)

        record_dict = record.__dict__
        extra: Dict[str, Any] = record_dict.get('extra') or {}

        log_rec = {
            "time": time_str,
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
