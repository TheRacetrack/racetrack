from __future__ import annotations
import json
import logging
import os
import random
from datetime import timezone, datetime
from typing import Optional, Any

logger = logging.getLogger('racetrack')


class JobEntrypoint:
    def __init__(self):
        set_logging_formatter(JSONFormatter())

    def perform(self) -> float:
        caller_name = self.get_caller_name()
        logger.debug(f'perform was called by {caller_name}')
        return random.random()

    def get_caller_name(self) -> Optional[str]:
        request = getattr(self, 'request_context').get()
        return request.headers.get('X-Caller-Name')


def set_logging_formatter(formatter: logging.Formatter):
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)


class JSONFormatter(logging.Formatter):
    def __init__(self, extra_logging: dict[str, Any] | None = None) -> None:
        super().__init__()
        self._ignore_keys: set[str] = {'msg', 'args', 'created', 'levelname', 'exc_text', 'exc_info', 'stack_info'}
        self._extra_logging: dict[str, Any] = extra_logging

    def format(self, record: logging.LogRecord) -> str:
        log_dict: dict[str, Any] = {
            'time': datetime.fromtimestamp(record.created, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'level': record.levelname,
            'message': record.getMessage(),
        }

        rdict = record.__dict__.copy()
        for key in rdict.keys():
            if key not in self._ignore_keys:
                log_dict[key] = rdict[key]

        if self._extra_logging:
            log_dict.update(self._extra_logging)

        if "JOB_NAME" in os.environ:
            log_dict["job_name"] = os.environ["JOB_NAME"]
        if "JOB_VERSION" in os.environ:
            log_dict["job_version"] = os.environ["JOB_VERSION"]

        if record.exc_info and record.exc_text is None:
            record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            log_dict["exc_info"] = record.exc_text

        if record.stack_info:
            log_dict["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(log_dict)
