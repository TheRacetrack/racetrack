import logging
import os
import sys
from typing import Optional

import loguru

LOG_FORMAT = '\033[2m[%(asctime)s]\033[0m %(levelname)s %(message)s'
LOG_FORMAT_DEBUG = '\033[2m[%(asctime)s]\033[0m %(name)s %(filename)s %(lineno)s %(levelname)s %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

structured_logs_on: bool = os.environ.get('STRUCTURED_LOGGING', 'false').lower() in {'true', 't', 'yes', 'y', '1'}


def configure_logs(log_level: Optional[str] = None):
    """Configure root logger with a log level"""
    log_level = log_level or os.environ.get('LOG_LEVEL', 'debug')
    level = _get_logging_level(log_level)
    # Set root level to INFO to avoid printing a ton of garbage DEBUG logs from imported libraries
    # Proper log level is set on racetrack logger
    logging.basicConfig(stream=sys.stdout, format=LOG_FORMAT, level=logging.INFO, datefmt=LOG_DATE_FORMAT, force=True)

    for handler in logging.getLogger().handlers:
        handler.setFormatter(ColoredFormatter(handler.formatter))

    root_logger = logging.getLogger('racetrack')
    root_logger.setLevel(level)

    loguru.logger.remove()
    loguru_config = {
        'colorize': None,
        'level': log_level.upper(),
        'format': "<dim>[{time:YYYY-MM-DD HH:mm:ss}]</dim> <lvl>{level}</lvl> {message}",
    }
    if structured_logs_on:
        loguru_config['serialize'] = True
    loguru.logger.add(sys.stdout, **loguru_config)


def get_logger(logger_name: str) -> logging.Logger:
    """Get configured racetrack logger"""
    if structured_logs_on:
        return loguru.logger
    else:
        return logging.getLogger('racetrack').getChild(logger_name)


logger = get_logger(__name__)


def _get_logging_level(str_level: str) -> int:
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
