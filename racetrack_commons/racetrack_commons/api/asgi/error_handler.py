from __future__ import annotations
import json
import sys
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from racetrack_client.log.errors import EntityNotFound, AlreadyExists, ValidationError
from racetrack_commons.api.metrics import metric_internal_server_errors
from racetrack_commons.api.tracing import log_request_exception_with_tracing
from racetrack_commons.auth.auth import UnauthorizedError


def register_error_handlers(api: FastAPI):

    @api.exception_handler(ValueError)
    def value_error_handler(request: Request, error: ValueError):
        """Bad Request error"""
        log_request_exception_with_tracing(request, error)
        return JSONResponse(
            content={'error': str(error), 'type': type(error).__name__},
            status_code=400,
        )

    @api.exception_handler(UnauthorizedError)
    def unauthorized_error_handler(request: Request, error: UnauthorizedError):
        """Unauthorized error"""
        log_request_exception_with_tracing(request, error)
        return JSONResponse(
            content={'error': str(error), 'type': type(error).__name__},
            status_code=401,
        )

    @api.exception_handler(EntityNotFound)
    def not_found_error_handler(request: Request, error: EntityNotFound):
        """Not Found error"""
        log_request_exception_with_tracing(request, error)
        return JSONResponse(
            content={'error': str(error), 'type': type(error).__name__},
            status_code=404,
        )

    @api.exception_handler(AlreadyExists)
    def conflict_error_handler(request: Request, error: AlreadyExists):
        """Already Exists - Conflict error"""
        log_request_exception_with_tracing(request, error)
        return JSONResponse(
            content={'error': str(error), 'type': type(error).__name__},
            status_code=409,
        )

    @api.exception_handler(ValidationError)
    def validation_error_handler(request: Request, error: AlreadyExists):
        """Validation Error"""
        return JSONResponse(
            content={'error': str(error), 'type': type(error).__name__},
            status_code=400,  # Bad Request
        )

    @api.exception_handler(Exception)
    def default_error_handler(request: Request, error: Exception):
        """Internal Server error"""
        metric_internal_server_errors.inc()
        log_request_exception_with_tracing(request, error)
        error_message, error_type = _upack_error_message(error)
        return JSONResponse(
            status_code=500,
            content={'error': error_message, 'type': error_type},
        )

    api.add_middleware(ErrorHandlerMiddleware)


class ErrorHandlerMiddleware:
    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        self.app: ASGIApp = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except BaseException as error:
            metric_internal_server_errors.inc()
            request = Request(scope=scope)
            log_request_exception_with_tracing(request, error)
            error_message, error_type = _upack_error_message(error)
            json_content = {'error': error_message, 'type': error_type}
            await send_json_content(send, 500, json_content)


async def send_json_content(send: Send, status_code: int, json_content: Any):
    await send({
        "type": "http.response.start",
        "status": status_code,
        "headers": [
            [b"content-type", b"application/json"],
        ],
    })
    await send({
        "type": "http.response.body",
        "body": json.dumps(json_content).encode(),
    })


def _upack_error_message(e: BaseException) -> tuple[str, str]:
    if sys.version_info[:2] < (3, 11) or not isinstance(e, ExceptionGroup):
        return str(e), type(e).__name__
    eg: ExceptionGroup = e

    sub_messages: list[str] = []
    sub_types: list[str] = []
    for suberror in eg.exceptions:
        sub_message, sub_type = _upack_error_message(suberror)
        sub_messages.append(sub_message)
        sub_types.append(sub_type)

    if len(sub_messages) == 1:
        e_message = sub_messages[0]
        e_type = sub_types[0]
    else:
        e_message = f'{e}: ' + ', '.join(sub_messages)
        e_type = f'{type(e).__name__}: ' + ', '.join(sub_types)
    return e_message, e_type
