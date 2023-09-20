from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from exceptiongroup import ExceptionGroup

from racetrack_client.log.errors import EntityNotFound, AlreadyExists, ValidationError
from racetrack_commons.api.metrics import metric_internal_server_errors
from racetrack_commons.api.tracing import log_request_exception_with_tracing
from racetrack_commons.auth.auth import UnauthorizedError


def register_error_handlers(api: FastAPI):

    @api.exception_handler(ValueError)
    async def value_error_handler(request: Request, error: ValueError):
        """Bad Request error"""
        log_request_exception_with_tracing(request, error)
        return JSONResponse(
            content={"error": str(error), "type": type(error).__name__},
            status_code=400,
        )

    @api.exception_handler(UnauthorizedError)
    async def unauthorized_error_handler(request: Request, error: UnauthorizedError):
        """Unauthorized error"""
        log_request_exception_with_tracing(request, error)
        return JSONResponse(
            content={"error": str(error), "type": type(error).__name__},
            status_code=401,
        )

    @api.exception_handler(EntityNotFound)
    async def not_found_error_handler(request: Request, error: EntityNotFound):
        """Not Found error"""
        log_request_exception_with_tracing(request, error)
        return JSONResponse(
            content={"error": str(error), "type": type(error).__name__},
            status_code=404,
        )

    @api.exception_handler(AlreadyExists)
    async def conflict_error_handler(request: Request, error: AlreadyExists):
        """Already Exists - Conflict error"""
        log_request_exception_with_tracing(request, error)
        return JSONResponse(
            content={"error": str(error), "type": type(error).__name__},
            status_code=409,
        )

    @api.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, error: AlreadyExists):
        """Validation Error"""
        return JSONResponse(
            content={"error": str(error), "type": type(error).__name__},
            status_code=400,  # Bad Request
        )

    @api.exception_handler(Exception)
    async def default_error_handler(request: Request, error: Exception):
        """Internal Server error"""
        metric_internal_server_errors.inc()
        log_request_exception_with_tracing(request, error)
        error_message, error_type = _upack_error_message(error)
        return JSONResponse(
            status_code=500,
            content={'error': error_message, "type": error_type},
        )

    @api.middleware('http')
    async def catch_all_exceptions_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except ExceptionGroup as e:
            metric_internal_server_errors.inc()
            log_request_exception_with_tracing(request, e)
            error_message, error_type = _upack_error_message(e)
            return JSONResponse(
                status_code=500,
                content={'error': error_message, "type": error_type},
            )
        except BaseException as error:
            metric_internal_server_errors.inc()
            log_request_exception_with_tracing(request, error)
            return JSONResponse(
                status_code=500,
                content={'error': str(error), "type": type(error).__name__},
            )


def _upack_error_message(e: BaseException) -> tuple[str, str]:
    if isinstance(e, ExceptionGroup):
        sub_messages: list[str] = []
        sub_types: list[str] = []
        for suberror in e.exceptions:
            sub_message, sub_type = _upack_error_message(suberror)
            sub_messages.append(sub_message)
            sub_types.append(sub_type)

        e_type = f'{type(e).__name__}: ' + ', '.join(sub_types)
        if len(sub_messages) == 1:
            e_message = sub_messages[0]
        else:
            e_message = f'{e}: ' + ', '.join(sub_messages)
        return e_message, e_type

    return str(e), type(e).__name__
