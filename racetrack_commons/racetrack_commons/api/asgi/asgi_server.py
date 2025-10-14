import contextlib
import signal
import sys
import threading
import time
from typing import Union, Callable, Optional
import logging

import uvicorn
from uvicorn.config import LOGGING_CONFIG
from uvicorn.logging import DefaultFormatter, AccessFormatter
from starlette.types import ASGIApp

from racetrack_client.log.exception import log_exception
from racetrack_client.log.logs import get_logger, ColoredFormatter
from racetrack_client.utils.env import is_env_flag_enabled
from racetrack_commons.api.debug import is_deployment_local

logger = get_logger(__name__)

# Don't print these access logs if occurred
HIDDEN_ACCESS_LOGS = {
    'GET /live 200',
    'GET /live/ 200',
    'GET /ready 200',
    'GET /ready/ 200',
    'GET /health 200',
    'GET /health/ 200',
    'GET /metrics 200',
    'GET /metrics/ 200',
}

UVICORN_DEBUG_LOGS = False


def serve_asgi_app(
    app: Union[ASGIApp, str],
    http_port: int,
    http_addr: str = '0.0.0.0',
    access_log: bool = False,
    on_shutdown: Optional[Callable[[], None]] = None
):
    use_reloader = is_deployment_local() and isinstance(app, str)
    mode_info = ' in RELOAD mode' if use_reloader else ''
    logger.info(f'Running ASGI server on http://{http_addr}:{http_port}{mode_info}')
    _setup_uvicorn_logs(access_log)

    config = uvicorn.Config(
        app=app,
        host=http_addr,
        port=http_port,
        log_level="debug",
        reload=use_reloader,
        timeout_graceful_shutdown=3,
    )
    server = ManagableServer(config)

    def shutdown_signal_handler(sig, frame):
        logger.info(f'received signal {sig}, shutting down...')
        if on_shutdown is not None:
            try:
                on_shutdown()
            except BaseException as e:
                log_exception(e)
        server.should_exit = True

    signal.signal(signal.SIGTERM, shutdown_signal_handler)
    signal.signal(signal.SIGINT, shutdown_signal_handler)

    server.run()


def serve_asgi_in_background(
    app: Union[ASGIApp, str],
    http_port: int,
    http_addr: str = '0.0.0.0',
    access_log: bool = False,
) -> contextlib.AbstractContextManager:
    logger.info(f'Running ASGI server in background on http://{http_addr}:{http_port}')
    _setup_uvicorn_logs(access_log)
    config = uvicorn.Config(
        app=app,
        host=http_addr,
        port=http_port,
        log_level="debug",
        timeout_graceful_shutdown=3,
    )
    return BackgroundServer(config=config).run_in_thread()


def _setup_uvicorn_logs(access_log: bool):
    if sys.stdout.isatty():
        LOGGING_CONFIG["formatters"]["default"]["fmt"] = "\033[2m[%(asctime)s]\033[0m %(levelname)s %(name)s: %(message)s"
    else:
        LOGGING_CONFIG["formatters"]["default"]["fmt"] = "[%(asctime)s] %(levelname)s %(message)s"
    LOGGING_CONFIG["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
    LOGGING_CONFIG["formatters"]["default"]["()"] = "racetrack_commons.api.asgi.asgi_server.ColoredDefaultFormatter"

    if sys.stdout.isatty():
        LOGGING_CONFIG["formatters"]["access"]["fmt"] = "\033[2m[%(asctime)s]\033[0m %(levelname)s %(name)s: %(request_line)s %(status_code)s"
    else:
        LOGGING_CONFIG["formatters"]["access"]["fmt"] = "[%(asctime)s] %(levelname)s %(request_line)s %(status_code)s"
    LOGGING_CONFIG["formatters"]["access"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
    LOGGING_CONFIG["formatters"]["access"]["()"] = "racetrack_commons.api.asgi.asgi_server.ColoredAccessFormatter"

    LOGGING_CONFIG["handlers"]["default"]["stream"] = 'ext://sys.stdout'
    LOGGING_CONFIG["handlers"]["default"]["level"] = 'INFO'
    LOGGING_CONFIG["handlers"]["access"]["stream"] = 'ext://sys.stdout'
    LOGGING_CONFIG["handlers"]["access"]["level"] = 'INFO'
    LOGGING_CONFIG["handlers"]["access"]["filters"] = ['needless_requests']

    LOGGING_CONFIG["filters"] = {
        "needless_requests": {
            "()": 'racetrack_commons.api.asgi.asgi_server.NeedlessRequestsFilter',
        },
    }

    LOGGING_CONFIG["loggers"]["uvicorn"]["propagate"] = False
    LOGGING_CONFIG["loggers"]["uvicorn"]["level"] = 'INFO'
    LOGGING_CONFIG["loggers"]["uvicorn"]["handlers"] = ['default']
    LOGGING_CONFIG["loggers"]["uvicorn.error"]["propagate"] = False
    LOGGING_CONFIG["loggers"]["uvicorn.error"]["level"] = 'ERROR'
    LOGGING_CONFIG["loggers"]["uvicorn.error"]["handlers"] = ['default']
    if UVICORN_DEBUG_LOGS:
        LOGGING_CONFIG["loggers"]["uvicorn"]["level"] = 'DEBUG'
        LOGGING_CONFIG["loggers"]["uvicorn.error"]["level"] = 'DEBUG'
        LOGGING_CONFIG["handlers"]["default"]["level"] = 'DEBUG'
        LOGGING_CONFIG["handlers"]["access"]["level"] = 'DEBUG'

    if not access_log:
        LOGGING_CONFIG["loggers"]["uvicorn.access"]["level"] = 'CRITICAL'
        LOGGING_CONFIG["loggers"]["uvicorn.access"]["handlers"] = []

    if is_env_flag_enabled('LOG_STRUCTURED', 'false'):
        LOGGING_CONFIG["formatters"]["default"]["()"] = "racetrack_client.log.logs.StructuredFormatter"
        LOGGING_CONFIG["formatters"]["access"]["()"] = "racetrack_client.log.logs.StructuredFormatter"


class ColoredDefaultFormatter(logging.Formatter):
    def __init__(self, **kwargs):
        logging.Formatter.__init__(self)
        self.colored_formatter = ColoredFormatter(DefaultFormatter(**kwargs))

    def format(self, record: logging.LogRecord):
        return self.colored_formatter.format(record)


class ColoredAccessFormatter(logging.Formatter):
    def __init__(self, **kwargs):
        logging.Formatter.__init__(self)
        self.colored_formatter = ColoredFormatter(AccessFormatter(**kwargs))

    def format(self, record: logging.LogRecord):
        return self.colored_formatter.format(record)


class NeedlessRequestsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        method: str = record.args[1]  # type: ignore
        uri: str = record.args[2]  # type: ignore
        response_code: int = record.args[4]  # type: ignore
        log_line = f'{method} {uri} {response_code}'
        if log_line in HIDDEN_ACCESS_LOGS:
            return False
        return True


class BackgroundServer(uvicorn.Server):
    def install_signal_handlers(self):
        pass

    @contextlib.contextmanager
    def run_in_thread(self):
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            self.should_exit = True
            thread.join()


class ManagableServer(uvicorn.Server):
    def install_signal_handlers(self):
        pass
