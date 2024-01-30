import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import loguru
from loguru._logger import Logger

from racetrack_client.utils.env import is_env_flag_enabled

LOG_FORMAT = '\033[2m[%(asctime)s]\033[0m %(levelname)s %(message)s'
LOG_FORMAT_DEBUG = '\033[2m[%(asctime)s]\033[0m %(name)s %(filename)s %(lineno)s %(levelname)s %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

structured_logs_on: bool = is_env_flag_enabled('STRUCTURED_LOGGING', 'false')
log_caller_enabled: bool = is_env_flag_enabled('LOG_CALLER_NAME', 'false')

logger: Logger = loguru.logger


def configure_logs(log_level: Optional[str] = None):
    """Configure root logger with a log level"""
    log_level = log_level or os.environ.get('LOG_LEVEL', 'debug')
    level = _parse_logging_level(log_level)
    # Set root level to INFO to avoid printing a ton of garbage DEBUG logs from imported libraries
    logging.basicConfig(stream=sys.stdout, format=LOG_FORMAT, level=logging.INFO, datefmt=LOG_DATE_FORMAT, force=True)

    for handler in logging.getLogger().handlers:
        handler.setFormatter(ColoredFormatter(handler.formatter))

    root_logger = logging.getLogger('racetrack')
    root_logger.setLevel(level)

    logger.remove()
    loguru_config = {
        'colorize': None,
        'level': log_level.upper(),
    }
    if structured_logs_on:
        def sink_serializer(message):
            record = message.record
            timestamp = datetime.fromtimestamp(record["time"].timestamp(), tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            simplified = {
                "time": timestamp,
                "level": record["level"].name,
                "message": record["message"],
                **record.get("extra", {}),
            }
            serialized = json.dumps(simplified)
            print(serialized, file=sys.stdout)

        loguru_config['serialize'] = True
        logger.add(sink_serializer, **loguru_config)
    else:
        def formatter(record):
            if record['level'].name == 'INFO':
                record['level'].name = 'INFO '
            extra = record.get('extra')
            tracing_id = extra.get('tracing_id')
            caller_name = extra.get('caller_name')
            if 'tracing_id' in extra:
                del extra['tracing_id']
            if 'caller_name' in extra:
                del extra['caller_name']

            if tracing_id and caller_name and log_caller_enabled:
                record['message'] = f"[{tracing_id}] <{caller_name}> " + record['message']
            elif tracing_id:
                record['message'] = f"[{tracing_id}] " + record['message']
            elif caller_name and log_caller_enabled:
                record['message'] = f"<{caller_name}> " + record['message']

            if extra:
                extra_str = _format_extra_vars(extra)
                return "<dim>[{time:YYYY-MM-DD HH:mm:ss}]</dim> <lvl>{level}</lvl> {message} " + extra_str + "\n"
            else:
                return "<dim>[{time:YYYY-MM-DD HH:mm:ss}]</dim> <lvl>{level}</lvl> {message}\n"

        loguru_config['format'] = formatter
        logger.add(sys.stdout, **loguru_config)

    logger.level("INFO", color="<blue>")
    logger.level("DEBUG", color="<green>")


def get_logger(_logger_name: Optional[str] = None) -> Logger:
    """Get configured racetrack logger"""
    return logger


def _format_extra_vars(extra: Dict[str, Any]) -> str:
    if len(extra) == 0:
        return ''
    keys = extra.keys()
    parts = [_format_extra_var(key, extra[key]) for key in keys]
    return " ".join(parts)


def _format_extra_var(var: str, val: Any) -> str:
    val = str(val)
    if ' ' in val:
        return f'<green>{var}="{val}"</green>'
    else:
        return f'<green>{var}={val}</green>'


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

    def format(self, record: logging.LogRecord):
        if record.levelname in self.log_level_templates:
            record.levelname = self.log_level_templates[record.levelname].format(record.levelname)
        return self.plain_formatter.format(record)
