import inspect
import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Tuple, Union
from contextvars import ContextVar

from fastapi import Body, FastAPI, APIRouter, Request, Response

from fatman_wrapper.webview import setup_webview_endpoints
from fatman_wrapper.docs import get_input_example, get_perform_docs
from fatman_wrapper.entrypoint import (
    FatmanEntrypoint,
    perform_entrypoint,
    list_entrypoint_parameters,
    list_auxiliary_endpoints,
    list_static_endpoints,
)
from fatman_wrapper.health import setup_health_endpoints, HealthState
from fatman_wrapper.metrics import (
    metric_request_duration,
    metric_request_internal_errors,
    metric_requests_started,
    metric_endpoint_requests_started,
    metric_requests_done,
    metric_last_call_timestamp,
    setup_entrypoint_metrics,
)
from fatman_wrapper.response import register_fatman_json_encoder
from racetrack_client.log.logs import get_logger
from racetrack_commons.api.asgi.fastapi import create_fastapi
from racetrack_commons.api.asgi.proxy import mount_at_base_path
from racetrack_commons.api.metrics import setup_metrics_endpoint
from racetrack_commons.auth.methods import get_racetrack_authorizations_methods
from racetrack_commons.telemetry.otlp import setup_opentelemetry

logger = get_logger(__name__)


def create_health_app(health_state: HealthState) -> FastAPI:
    """
    Create temporary app serving liveness & readiness endpoints until the actual Fatman entrypoint loads up.
    """
    fatman_name = os.environ.get('FATMAN_NAME', '')
    fatman_version = os.environ.get('FATMAN_VERSION')
    base_url = f'/pub/fatman/{fatman_name}/{fatman_version}'

    fastapi_app = create_fastapi(
        title=f'Fatman - {fatman_name}',
        description='Fatman Module wrapped in a REST server',
        base_url=base_url,
        version=fatman_version,
        request_access_log=True,
    )

    setup_health_endpoints(fastapi_app, health_state, fatman_name)

    return mount_at_base_path(fastapi_app, '/pub/fatman/{fatman_name}/{version}')


def create_api_app(
    entrypoint: FatmanEntrypoint,
    health_state: HealthState,
) -> FastAPI:
    """Create FastAPI app and register all endpoints without running a server"""
    fatman_name = os.environ.get('FATMAN_NAME', '')
    fatman_version = os.environ.get('FATMAN_VERSION')
    base_url = f'/pub/fatman/{fatman_name}/{fatman_version}'

    fastapi_app = create_fastapi(
        title=f'Fatman - {fatman_name}',
        description='Fatman Module wrapped in a REST server',
        base_url=base_url,
        version=fatman_version,
        authorizations=get_racetrack_authorizations_methods(),
        request_access_log=True,
        response_access_log=True,
    )
    register_fatman_json_encoder()

    setup_health_endpoints(fastapi_app, health_state, fatman_name)
    setup_entrypoint_metrics(entrypoint)
    setup_metrics_endpoint(fastapi_app)

    api_router = APIRouter(tags=['API'])
    _setup_api_endpoints(api_router, entrypoint, fastapi_app, base_url)
    _setup_request_context(entrypoint, fastapi_app)
    fastapi_app.include_router(api_router, prefix="/api/v1")

    if os.environ.get('OPENTELEMETRY_ENDPOINT'):
        setup_opentelemetry(fastapi_app, os.environ.get('OPENTELEMETRY_ENDPOINT'), {
            'service.name': 'fatman',
            'fatman_name': fatman_name,
            'fatman_version': fatman_version,
        })

    return mount_at_base_path(fastapi_app, '/pub/fatman/{fatman_name}/{version}')


def _setup_api_endpoints(
    api: APIRouter,
    entrypoint: FatmanEntrypoint,
    fastapi_app: FastAPI,
    base_url: str,
):
    _setup_perform_endpoint(api, entrypoint)
    _setup_auxiliary_endpoints(api, entrypoint)
    _setup_static_endpoints(api, entrypoint)
    setup_webview_endpoints(entrypoint, base_url, fastapi_app, api)


def _setup_perform_endpoint(api: APIRouter, entrypoint: FatmanEntrypoint):
    example_input = get_input_example(entrypoint, endpoint='/perform')

    endpoint_path = '/perform'
    summary = "Call main action"
    description = "Call main action"
    perform_docs = get_perform_docs(entrypoint)
    if perform_docs:
        description = f"Call main action: {perform_docs}"

    @api.post(
        '/perform',
        summary=summary,
        description=description,
    )
    def _perform_endpoint(payload: Dict[str, Any] = Body(default=example_input)):
        """Call main action"""
        metric_requests_started.inc()
        metric_endpoint_requests_started.labels(endpoint=endpoint_path).inc()
        start_time = time.time()
        try:
            assert payload is not None, 'payload is empty'
            result = perform_entrypoint(entrypoint, payload)
            return result
        except BaseException as e:
            metric_request_internal_errors.labels(endpoint=endpoint_path).inc()
            raise e
        finally:
            metric_request_duration.labels(endpoint=endpoint_path).observe(time.time() - start_time)
            metric_requests_done.inc()
            metric_last_call_timestamp.set(time.time())

    @api.get('/parameters')
    def _get_parameters():
        """Return required arguments & optional parameters that model accepts"""
        return list_entrypoint_parameters(entrypoint)


def _setup_auxiliary_endpoints(api: APIRouter, entrypoint: FatmanEntrypoint):
    """Configure custom auxiliary endpoints defined by user in an entypoint"""
    auxiliary_endpoints = list_auxiliary_endpoints(entrypoint)
    for endpoint_path in sorted(auxiliary_endpoints.keys()):

        endpoint_method: Callable = auxiliary_endpoints[endpoint_path]
        endpoint_name = endpoint_path.replace('/', '_')

        example_input = get_input_example(entrypoint, endpoint=endpoint_path)

        if not endpoint_path.startswith('/'):
            endpoint_path = '/' + endpoint_path

        # keep these variables inside closure as next loop cycle will overwrite it
        def _add_endpoint(endpoint_path: str, endpoint_method: Callable):

            summary = f"Call auxiliary endpoint: {endpoint_path}"
            description = "Call auxiliary endpoint"
            endpoint_docs = inspect.getdoc(endpoint_method)
            if endpoint_docs:
                description = f"Call auxiliary endpoint: {endpoint_docs}"

            @api.post(
                endpoint_path,
                operation_id=f'auxiliary_endpoint_{endpoint_name}',
                summary=summary,
                description=description,
            )
            def _auxiliary_endpoint(
                payload: Dict[str, Any] = Body(default=example_input),
            ):
                metric_requests_started.inc()
                metric_endpoint_requests_started.labels(endpoint=endpoint_path).inc()
                start_time = time.time()
                try:
                    assert payload is not None, 'payload is empty'
                    return endpoint_method(**payload)
                except TypeError as e:
                    metric_request_internal_errors.labels(endpoint=endpoint_path).inc()
                    raise ValueError(f'failed to call a function: {e}')
                except BaseException as e:
                    metric_request_internal_errors.labels(endpoint=endpoint_path).inc()
                    raise e
                finally:
                    metric_request_duration.labels(endpoint=endpoint_path).observe(time.time() - start_time)
                    metric_requests_done.inc()
                    metric_last_call_timestamp.set(time.time())

        _add_endpoint(endpoint_path, endpoint_method)

        logger.info(f'configured auxiliary endpoint: {endpoint_path}')


def _setup_static_endpoints(api: APIRouter, entrypoint: FatmanEntrypoint):
    """Configure custom static endpoints defined by user in an entypoint"""
    static_endpoints = list_static_endpoints(entrypoint)
    for endpoint_path in sorted(static_endpoints.keys()):
        static_file = static_endpoints[endpoint_path]
        _setup_static_endpoint(api, entrypoint, endpoint_path, static_file)


def _setup_static_endpoint(
    api: APIRouter,
    entrypoint: FatmanEntrypoint,
    endpoint_path: str,
    static_file: Union[Tuple, str],
):
    """
    Configure custom static endpoints defined by user in an entypoint
    :param api: FastAPI API namespace
    :param entrypoint: Fatman entrypoint instance
    :param endpoint_path: endpoint path, eg. /ui/index
    :param static_file: static file path or tuple of (path, mimetype)
    """
    # in case of directory, serve subfiles recursively
    if isinstance(static_file, str):
        static_file_path = Path(static_file)
        if static_file_path.is_dir():
            for subfile in static_file_path.iterdir():
                endpoint_subpath = endpoint_path + '/' + subfile.name
                _setup_static_endpoint(api, entrypoint, endpoint_subpath, str(subfile))
            return

    filepath, mimetype = _get_static_file_with_mimetype(static_file)

    if not endpoint_path.startswith('/'):
        endpoint_path = '/' + endpoint_path

    @api.get(endpoint_path, operation_id=f'static_endpoint_{endpoint_path}')
    def _static_endpoint():
        """Fetch static file"""
        content = filepath.read_bytes()
        return Response(content=content, media_type=mimetype)

    logger.info(f'configured static endpoint: {endpoint_path} -> {filepath} ({mimetype})')


def _get_static_file_with_mimetype(static_file: Union[Tuple, str]) -> Tuple[Path, str]:
    if isinstance(static_file, tuple):
        filename = static_file[0]
        mimetype = static_file[1]
    elif isinstance(static_file, str):
        filename = static_file
        mimetype = None
    else:
        raise RuntimeError('static endpoint value should be string or tuple')
    path = Path(filename)
    assert path.is_file(), f"static file doesn't exist: {filename}"
    if not mimetype:
        mimetype, encoding = mimetypes.guess_type(path, strict=False)
        if not mimetype:
            mimetype = 'text/plain'
            logger.warning(f"Can't detect mimetype of static file {filename}, applying default {mimetype}")
    return path, mimetype


def _setup_request_context(entrypoint: FatmanEntrypoint, fastapi_app: FastAPI):
    request_context: ContextVar[Request] = ContextVar('request_context')
    setattr(entrypoint, 'request_context', request_context)

    @fastapi_app.middleware('http')
    async def request_context_middleware(request: Request, call_next) -> Response:
        request_id = request_context.set(request)
        response = await call_next(request)
        request_context.reset(request_id)
        return response
