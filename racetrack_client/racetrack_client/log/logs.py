import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import loguru

LOG_FORMAT = '\033[2m[%(asctime)s]\033[0m %(levelname)s %(message)s'
LOG_FORMAT_DEBUG = '\033[2m[%(asctime)s]\033[0m %(name)s %(filename)s %(lineno)s %(levelname)s %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

structured_logs_on: bool = os.environ.get('STRUCTURED_LOGGING', 'false').lower() in {'true', 't', 'yes', 'y', '1'}

logger: loguru._logger.Logger = loguru.logger


def configure_logs(log_level: Optional[str] = None):
    """Configure root logger with a log level"""
    log_level = log_level or os.environ.get('LOG_LEVEL', 'debug')
    level = _get_logging_level(log_level)
    # Set root level to INFO to avoid printing a ton of garbage DEBUG logs from imported libraries
    logging.basicConfig(stream=sys.stdout, format=LOG_FORMAT, level=logging.INFO, datefmt=LOG_DATE_FORMAT, force=True)

    for handler in logging.getLogger().handlers:
        handler.setFormatter(ColoredFormatter(handler.formatter))

    root_logger = logging.getLogger('racetrack')
    root_logger.setLevel(level)

    def formatter(record):
        if record['level'].name == 'INFO':
            record['level'].name = 'INFO '
        if record.get("extra"):
            return "<dim>[{time:YYYY-MM-DD HH:mm:ss}]</dim> <lvl>{level}</lvl> {message} {extra}\n"
        else:
            return "<dim>[{time:YYYY-MM-DD HH:mm:ss}]</dim> <lvl>{level}</lvl> {message}\n"

    logger.remove()
    loguru_config = {
        'colorize': None,
        'level': log_level.upper(),
        'format': formatter,
    }
    if structured_logs_on:
        def sink_serializer(message):
            record = message.record
            timestamp = datetime.fromtimestamp(record["time"].timestamp(), tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            simplified = {
                "timestamp": timestamp,
                "level": record["level"].name,
                "message": record["message"],
                **record.get("extra", {}),
            }
            serialized = json.dumps(simplified)
            print(serialized, file=sys.stdout)

        loguru_config['serialize'] = True
        logger.add(sink_serializer, **loguru_config)
    else:
        logger.add(sys.stdout, **loguru_config)

    logger.level("INFO", color="<blue>")
    logger.level("DEBUG", color="<green>")


def get_logger(logger_name: Optional[str] = None) -> loguru._logger.Logger:
    """Get configured racetrack logger"""
    return logger


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
